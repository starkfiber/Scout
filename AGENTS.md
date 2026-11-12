# Scout engineering boundary

The repository contains code and generic documentation only. Never add a user's home directory index, file inventory, credentials, chat content, backups, logs or screenshots with private paths to Git. Keep the SQLite index under the user's local Application Support directory. Preserve the read-only file API until every mutation has a review and recovery design. Do not report open handles as confirmed reads, or folder blocks as physical NAND placement. The RF² native probe is a scoped experiment; benchmark the complete scanner before making performance claims.
