local ap_globals = {}
local seen = {}

local docs_file = io.open(".ardupilot/docs.lua", "r")
if docs_file then
    for line in docs_file:lines() do
        -- Match global function definitions: function millis()
        local func = line:match("^function%s+([%a_][%w_]*)%s*%(")
        if func and not seen[func] then
            seen[func] = true
            table.insert(ap_globals, func)
        end
        -- Match global table / object definitions: logger = {}
        local var = line:match("^([%a_][%w_]*)%s*=")
        if var and not seen[var] then
            seen[var] = true
            table.insert(ap_globals, var)
        end
    end
    docs_file:close()
end

stds.ardupilot = {
    globals = ap_globals
}

std = "lua53+ardupilot"

-- Ignore the docs file and any virtual environments if you run `luacheck .`
exclude_files = {
    ".ardupilot",
    ".venv"
}
