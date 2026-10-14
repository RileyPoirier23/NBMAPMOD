-- RCMP uniforms in police station lockers / storage.
require "Items/ProceduralDistributions"

local ITEMS = {
    { "Base.Shirt_RCMPGrey", 6 }, { "Base.Trousers_RCMP", 6 }, { "Base.Hat_RCMPForage", 4 },
    { "Base.Vest_BulletRCMP", 3 }, { "Base.Jacket_RCMPSerge", 1 }, { "Base.Hat_RCMPStetson", 1 },
    { "Base.Tshirt_RCMPGrey", 4 },
}

local function addToPoliceContainers()
    if not ProceduralDistributions or not ProceduralDistributions.list then return end
    for name, dist in pairs(ProceduralDistributions.list) do
        if type(name) == "string" and name:find("^Police") and dist.items then
            for _, it in ipairs(ITEMS) do
                table.insert(dist.items, it[1])
                table.insert(dist.items, it[2])
            end
        end
    end
end

addToPoliceContainers()
Events.OnPreDistributionMerge.Add(addToPoliceContainers)
