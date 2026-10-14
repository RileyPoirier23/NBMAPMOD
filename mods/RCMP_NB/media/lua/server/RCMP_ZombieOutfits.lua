-- Swap every police zombie outfit for its RCMP counterpart.
-- ZombiesZoneDefinition is vanilla's zone -> outfit table (media/lua/server/ZombiesZoneDefinition.lua).
local RENAME = {
    Police = "RCMP",
    PoliceState = "RCMP",
    PoliceRiot = "RCMPRiot",
    PoliceGrey = "RCMP",
    PoliceBlue = "RCMP",
}

local function patchZoneDefinitions()
    if not ZombiesZoneDefinition then return end
    local n = 0
    for zone, list in pairs(ZombiesZoneDefinition) do
        if type(list) == "table" then
            for _, entry in ipairs(list) do
                if type(entry) == "table" and entry.name and RENAME[entry.name] then
                    entry.name = RENAME[entry.name]
                    n = n + 1
                end
            end
        end
    end
    print("[RCMP_NB] re-pointed " .. n .. " zombie outfit entries to RCMP outfits")
end

patchZoneDefinitions()
Events.OnGameBoot.Add(patchZoneDefinitions)
