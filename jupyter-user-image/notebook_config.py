c = get_config()

# Disable file downloads
c.ContentsManager.hide_globs = ['*']

# Disable terminal
c.NotebookApp.terminals_enabled = False

# Security settings
c.NotebookApp.disable_check_xsrf = False
c.NotebookApp.allow_remote_access = True