#define _POSIX_C_SOURCE 200809L
#define _DARWIN_C_SOURCE 1
#include <errno.h>
#include <poll.h>
#include <signal.h>
#include <sqlite3.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

/* SQLite persistence bridge for the trusted RF2 directory/metadata service.
 * The RF2 process enumerates every folder; this process owns traversal and the
 * one transaction that makes a completed index visible. No file content reads.
 */
typedef struct { char *full, *rel; } Folder;
static char error_text[512];
static Folder *stack;
static size_t stack_count, stack_capacity;
static sqlite3 *db;
static sqlite3_stmt *upsert, *update_total, *totals_query;
static int service_in = -1, service_out = -1;
static pid_t service_pid = -1;
static uint64_t generation, seen;

static void fail(const char *message) {
    if (!error_text[0]) snprintf(error_text, sizeof error_text, "%s", message);
}

static void fail_sql(const char *action) {
    if (!error_text[0]) snprintf(error_text, sizeof error_text, "%s: %s", action, sqlite3_errmsg(db));
}

static int sql_exec(const char *sql) {
    char *detail = NULL;
    if (sqlite3_exec(db, sql, NULL, NULL, &detail) == SQLITE_OK) return 1;
    if (!error_text[0]) snprintf(error_text, sizeof error_text, "SQLite: %s", detail ? detail : sqlite3_errmsg(db));
    sqlite3_free(detail);
    return 0;
}

static int sql_prepare(sqlite3_stmt **stmt, const char *sql) {
    if (sqlite3_prepare_v2(db, sql, -1, stmt, NULL) == SQLITE_OK) return 1;
    fail_sql("prepare");
    return 0;
}

static int push(char *full, char *rel) {
    if (stack_count == stack_capacity) {
        size_t next = stack_capacity ? stack_capacity * 2 : 64;
        Folder *grown = realloc(stack, next * sizeof *stack);
        if (!grown) { fail("Out of memory while traversing folders"); return 0; }
        stack = grown;
        stack_capacity = next;
    }
    stack[stack_count++] = (Folder){full, rel};
    return 1;
}

static char *join(const char *parent, const char *name, int root_relative) {
    size_t a = strlen(parent), b = strlen(name);
    size_t extra = root_relative && !a ? 0 : 1;
    if (a + extra + b > 4095) { fail("Path exceeds RF2 service limit"); return NULL; }
    char *out = malloc(a + extra + b + 1);
    if (!out) { fail("Out of memory for path"); return NULL; }
    memcpy(out, parent, a);
    if (extra) out[a] = '/';
    memcpy(out + a + extra, name, b);
    out[a + extra + b] = 0;
    return out;
}

static int64_t as_millis(uint64_t seconds, uint32_t nanos) {
    return (int64_t)seconds * 1000 + nanos / 1000000;
}

static int write_node(const char *path, const char *name, const char *parent,
                      int kind, uint64_t bytes, uint64_t blocks, int64_t modified) {
    sqlite3_reset(upsert);
    sqlite3_clear_bindings(upsert);
    const char *kind_name = kind == 1 ? "folder" : kind == 2 ? "link" : "file";
    sqlite3_bind_text(upsert, 1, path, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(upsert, 2, name, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(upsert, 3, parent, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(upsert, 4, kind_name, -1, SQLITE_STATIC);
    if (kind == 0) {
        sqlite3_bind_int64(upsert, 5, (sqlite3_int64)bytes);
        sqlite3_bind_int64(upsert, 6, (sqlite3_int64)(blocks * 512));
    } else {
        sqlite3_bind_null(upsert, 5);
        sqlite3_bind_null(upsert, 6);
    }
    sqlite3_bind_int64(upsert, 7, modified);
    sqlite3_bind_int64(upsert, 8, (sqlite3_int64)generation);
    if (sqlite3_step(upsert) == SQLITE_DONE) { seen++; return 1; }
    fail_sql("index row");
    return 0;
}

static int read_exact(int fd, unsigned char *out, size_t length) {
    size_t used = 0;
    while (used < length) {
        struct pollfd p = {fd, POLLIN, 0};
        int ready = poll(&p, 1, 8000);
        if (ready <= 0) { fail(ready == 0 ? "RF2 service read timed out" : "RF2 service poll failed"); return 0; }
        ssize_t got = read(fd, out + used, length - used);
        if (got <= 0) { fail("RF2 service ended during scan"); return 0; }
        used += (size_t)got;
    }
    return 1;
}

static int write_exact(int fd, const unsigned char *data, size_t length) {
    size_t used = 0;
    while (used < length) {
        ssize_t count = write(fd, data + used, length - used);
        if (count <= 0) { fail("RF2 service request failed"); return 0; }
        used += (size_t)count;
    }
    return 1;
}

static uint32_t u32(const unsigned char *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static uint64_t u64(const unsigned char *p) {
    uint64_t value = 0;
    for (int i = 7; i >= 0; i--) value = value * 256 + p[i];
    return value;
}

static int start_service(const char *binary) {
    int to_child[2], from_child[2];
    if (pipe(to_child)) { fail("Cannot open RF2 service pipes"); return 0; }
    if (pipe(from_child)) { close(to_child[0]); close(to_child[1]); fail("Cannot open RF2 service pipes"); return 0; }
    service_pid = fork();
    if (service_pid < 0) {
        close(to_child[0]); close(to_child[1]); close(from_child[0]); close(from_child[1]);
        fail("Cannot start RF2 service"); return 0;
    }
    if (service_pid == 0) {
        dup2(to_child[0], STDIN_FILENO);
        dup2(from_child[1], STDOUT_FILENO);
        close(to_child[0]); close(to_child[1]); close(from_child[0]); close(from_child[1]);
        execl(binary, binary, (char *)NULL);
        _exit(127);
    }
    close(to_child[0]); close(from_child[1]);
    service_in = to_child[1]; service_out = from_child[0];
    return 1;
}

static int scan_folder(Folder *folder) {
    size_t path_length = strlen(folder->full);
    if (!path_length || path_length > 4095) { fail("Invalid RF2 folder path"); return 0; }
    unsigned char header[4] = {(unsigned char)path_length, (unsigned char)(path_length >> 8),
                               (unsigned char)(path_length >> 16), (unsigned char)(path_length >> 24)};
    if (!write_exact(service_in, header, 4) ||
        !write_exact(service_in, (const unsigned char *)folder->full, path_length)) return 0;
    for (;;) {
        if (!read_exact(service_out, header, 4)) return 0;
        uint32_t length = u32(header);
        if (!length) break;
        if (length == UINT32_MAX || length > 131072) { fail("RF2 service rejected a folder"); return 0; }
        unsigned char *chunk = malloc(length);
        if (!chunk) { fail("Out of memory for RF2 response"); return 0; }
        if (!read_exact(service_out, chunk, length)) { free(chunk); return 0; }
        for (size_t at = 0; at < length;) {
            if (length - at < 32) { free(chunk); fail("Short RF2 metadata record"); return 0; }
            size_t name_length = (size_t)chunk[at] | (size_t)chunk[at + 1] << 8;
            if (!name_length || name_length > 255 || at + 32 + name_length > length) {
                free(chunk); fail("Invalid RF2 metadata record"); return 0;
            }
            char name[256];
            memcpy(name, chunk + at + 32, name_length); name[name_length] = 0;
            if (memchr(name, 0, name_length) || memchr(name, '/', name_length)) {
                free(chunk); fail("Invalid filename in RF2 response"); return 0;
            }
            at += 32 + name_length;
            if (!strcmp(name, ".") || !strcmp(name, "..")) continue;
            char *full = join(folder->full, name, 0);
            char *rel = join(folder->rel, name, 1);
            if (!full || !rel) { free(full); free(rel); free(chunk); return 0; }
            size_t record_at = at - 32 - name_length;
            unsigned mode = (unsigned)chunk[record_at + 2] | (unsigned)chunk[record_at + 3] << 8;
            int kind = (mode & S_IFMT) == S_IFDIR ? 1 : (mode & S_IFMT) == S_IFLNK ? 2 : 0;
            uint64_t bytes = u64(chunk + record_at + 4);
            uint64_t blocks = u64(chunk + record_at + 12);
            int64_t modified = as_millis(u64(chunk + record_at + 20), u32(chunk + record_at + 28));
            if (!write_node(rel, name, folder->rel, kind, bytes, blocks, modified)) {
                free(full); free(rel); free(chunk); return 0;
            }
            if (kind == 1) {
                if (!push(full, rel)) { free(full); free(rel); free(chunk); return 0; }
            } else { free(full); free(rel); }
        }
        free(chunk);
    }
    printf("PROGRESS %llu\n", (unsigned long long)seen);
    fflush(stdout);
    return 1;
}

static int finish_index(const char *scope, int64_t started) {
    sqlite3_stmt *reset = NULL;
    if (!sql_prepare(&reset, "UPDATE nodes SET tree_allocated=0 WHERE generation=? AND kind='folder'")) return 0;
    sqlite3_bind_int64(reset, 1, (sqlite3_int64)generation);
    int reset_ok = sqlite3_step(reset) == SQLITE_DONE;
    if (!reset_ok) fail_sql("reset folder totals");
    sqlite3_finalize(reset);
    if (!reset_ok) return 0;
    const char *totals_sql =
        "WITH RECURSIVE walk(path,bytes) AS ("
        " SELECT parent,allocated FROM nodes WHERE generation=? AND kind='file' AND allocated IS NOT NULL"
        " UNION ALL SELECT n.parent,walk.bytes FROM walk JOIN nodes n ON n.path=walk.path WHERE walk.path<>?"
        ") SELECT path,SUM(bytes) FROM walk GROUP BY path";
    if (!sql_prepare(&totals_query, totals_sql)) return 0;
    sqlite3_bind_int64(totals_query, 1, (sqlite3_int64)generation);
    sqlite3_bind_text(totals_query, 2, scope, -1, SQLITE_TRANSIENT);
    if (!sql_prepare(&update_total, "UPDATE nodes SET tree_allocated=? WHERE path=? AND kind='folder'")) return 0;
    int step;
    while ((step = sqlite3_step(totals_query)) == SQLITE_ROW) {
        const unsigned char *path = sqlite3_column_text(totals_query, 0);
        sqlite3_reset(update_total); sqlite3_clear_bindings(update_total);
        sqlite3_bind_int64(update_total, 1, sqlite3_column_int64(totals_query, 1));
        sqlite3_bind_text(update_total, 2, (const char *)path, -1, SQLITE_TRANSIENT);
        if (sqlite3_step(update_total) != SQLITE_DONE) { fail_sql("folder total"); return 0; }
    }
    if (step != SQLITE_DONE) { fail_sql("sum folder totals"); return 0; }
    sqlite3_stmt *prune = NULL;
    const char *prune_sql = "DELETE FROM nodes WHERE generation<>? AND (?='' OR path=? OR substr(path,1,length(?)+1)=?||'/')";
    if (!sql_prepare(&prune, prune_sql)) return 0;
    sqlite3_bind_int64(prune, 1, (sqlite3_int64)generation);
    for (int i = 2; i <= 5; i++) sqlite3_bind_text(prune, i, scope, -1, SQLITE_TRANSIENT);
    int ok = sqlite3_step(prune) == SQLITE_DONE;
    if (!ok) fail_sql("prune old generation");
    sqlite3_finalize(prune);
    if (!ok) return 0;
    sqlite3_stmt *run = NULL;
    if (!sql_prepare(&run, "INSERT INTO scan_runs(generation,scope,started,ended,seen,engine) VALUES(?,?,?,CAST(strftime('%s','now') AS INTEGER)*1000,?,'rf2-native-index-bridge')")) return 0;
    sqlite3_bind_int64(run, 1, (sqlite3_int64)generation);
    sqlite3_bind_text(run, 2, scope, -1, SQLITE_TRANSIENT);
    sqlite3_bind_int64(run, 3, started);
    sqlite3_bind_int64(run, 4, (sqlite3_int64)seen);
    ok = sqlite3_step(run) == SQLITE_DONE;
    if (!ok) fail_sql("record completed scan");
    sqlite3_finalize(run);
    return ok;
}

int main(int argc, char **argv) {
    if (argc != 7) { fprintf(stderr, "usage: scout-index service root scope db generation started_ms\n"); return 2; }
    signal(SIGPIPE, SIG_IGN);
    const char *service = argv[1], *root = argv[2], *scope = argv[3], *db_path = argv[4];
    generation = strtoull(argv[5], NULL, 10);
    int64_t started = strtoll(argv[6], NULL, 10);
    if (!generation || strlen(root) > 4095 || strlen(scope) > 4095) { fail("Invalid scan arguments"); goto done; }
    if (sqlite3_open_v2(db_path, &db, SQLITE_OPEN_READWRITE, NULL) != SQLITE_OK) { fail_sql("open index"); goto done; }
    sqlite3_busy_timeout(db, 5000);
    if (!sql_exec("BEGIN IMMEDIATE")) goto done;
    const char *upsert_sql =
        "INSERT INTO nodes(path,name,parent,kind,bytes,allocated,tree_allocated,modified,generation)"
        " VALUES(?,?,?,?,?,?,NULL,?,?) ON CONFLICT(path) DO UPDATE SET"
        " name=excluded.name,parent=excluded.parent,kind=excluded.kind,bytes=excluded.bytes,"
        " allocated=excluded.allocated,tree_allocated=NULL,modified=excluded.modified,generation=excluded.generation";
    if (!sql_prepare(&upsert, upsert_sql)) goto done;
    struct stat root_stat;
    if (lstat(root, &root_stat) || !S_ISDIR(root_stat.st_mode)) { fail("Index root is unavailable"); goto done; }
    const char *root_name = strrchr(root, '/'); root_name = root_name ? root_name + 1 : root;
    char *root_parent = strdup(scope);
    if (!root_parent) { fail("Out of memory for root"); goto done; }
    char *slash = strrchr(root_parent, '/');
    if (slash) *slash = 0; else root_parent[0] = 0;
    int root_ok = write_node(scope, root_name, root_parent, 1, 0, 0,
                             (int64_t)root_stat.st_mtimespec.tv_sec * 1000 + root_stat.st_mtimespec.tv_nsec / 1000000);
    free(root_parent);
    if (!root_ok) goto done;
    char *root_copy = strdup(root), *scope_copy = strdup(scope);
    if (!root_copy || !scope_copy) {
        free(root_copy); free(scope_copy); fail("Out of memory for root folder"); goto done;
    }
    if (!push(root_copy, scope_copy)) { free(root_copy); free(scope_copy); goto done; }
    if (!start_service(service)) goto done;
    while (stack_count) {
        Folder current = stack[--stack_count];
        int ok = scan_folder(&current);
        free(current.full); free(current.rel);
        if (!ok) goto done;
    }
    if (!finish_index(scope, started)) goto done;
    if (!sql_exec("COMMIT")) goto done;
    printf("DONE %llu\n", (unsigned long long)seen); fflush(stdout);
done:
    if (error_text[0] && db) sqlite3_exec(db, "ROLLBACK", NULL, NULL, NULL);
    if (service_in >= 0) close(service_in);
    if (service_out >= 0) close(service_out);
    if (service_pid > 0) { int status; waitpid(service_pid, &status, 0); }
    while (stack_count) { free(stack[--stack_count].full); free(stack[stack_count].rel); }
    free(stack);
    sqlite3_finalize(upsert); sqlite3_finalize(update_total); sqlite3_finalize(totals_query);
    if (db) sqlite3_close(db);
    if (error_text[0]) { fprintf(stderr, "%s\n", error_text); return 1; }
    return 0;
}
