-- Terminal Launcher's WezTerm config, used ONLY for windows this tool opens
-- (passed via WEZTERM_CONFIG_FILE when we start the GUI). It exists to make a
-- launched workspace open MAXIMIZED: the first pane is created by `gui-startup`,
-- which maximizes the window; the launcher then splits the rest into that same
-- (already-maximized) window. initial_cols/rows are a large fallback so any
-- window that doesn't go through gui-startup still opens big rather than 80x24.
local wezterm = require 'wezterm'
local config = wezterm.config_builder()

config.initial_cols = 400
config.initial_rows = 120

wezterm.on('gui-startup', function(cmd)
  local _, _, window = wezterm.mux.spawn_window(cmd or {})
  window:gui_window():maximize()
end)

return config
