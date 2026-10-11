--[[
  DBDump.lua  --  dump the squad database files as the game loads them
  Football Life 2026 (eFootball PES 2021 / Smoke Patch), Sider 7

  WHY THIS EXISTS
  ---------------
  The squad database lives inside download\data_s2526.cpk as Konami-zlib
  ("WESYS") compressed .bin files. Rather than needing CPK extraction tools,
  Sider's livecpk_read event hands us each file's bytes as the game loads it,
  so we can just write them to disk. CommonLib.lua already uses this exact
  trick for CompetitionEntry.bin; this is the same pattern, generalised.

  Files land in SiderAddons\dbdump\ in two forms:
      <name>.bin        exactly as loaded (still WESYS-compressed)
      <name>.raw        decompressed payload, which is what we decode

  Large files arrive in several chunks, so accumulate until offset+len
  reaches total_size before writing.

  READ ONLY: this never rewrites anything the game reads. It is a dumper.
  Remove it from sider.ini once the files have been captured -- there is no
  reason to keep re-writing them on every launch.
]]

local m = {}

-- Basenames we want, lowercase. The game passes full paths like
-- "common\etc\pesdb\PlayerAssignment.bin".
local TARGETS = {
    ["playerassignment.bin"]        = true,
    ["player.bin"]                  = true,
    ["team.bin"]                    = true,
    ["playerappearance.bin"]        = true,
    ["specialplayerassignment.bin"] = true,
    -- Maps teams to competitions. CommonLib documents the competition IDs:
    -- 21 = Brasileirao Serie A, 90 = Serie B. Dumping this turns "which of 747
    -- teams is Flamengo" into "which of 20", which is the difference between a
    -- guessed team mapping and a correct one.
    ["competitionentry.bin"]        = true,
    ["competitionentry1.bin"]       = true,
    ["competitionentry2.bin"]       = true,
    ["competitionregulation.bin"]   = true,
}

local chunks = {}     -- filename -> { pieces }
local seen   = {}     -- filename -> how many complete copies have arrived
local outdir = nil

-- A Smoke Patch install loads a base database and then a patched one that
-- supersedes it. Writing only the FIRST copy per basename captured the stale
-- one -- which is why an override built from it had no effect in game. Number
-- every copy instead, and log the full path each came from.

local function basename(path)
    local b = string.match(path, "([^\\/]+)$")
    if b == nil then return string.lower(path) end
    return string.lower(b)
end

-- Konami container: 3 magic bytes, "WESYS", u32 compressed size,
-- u32 uncompressed size, then the zlib stream. Some files ship uncompressed,
-- in which case there is no header and the bytes are already the payload.
local function unwrap(data)
    if #data >= 16 and string.lower(string.sub(data, 4, 8)) == "wesys" then
        local usize = memory.unpack("u32", string.sub(data, 13, 16))
        if zlib == nil or zlib.uncompress == nil then
            return nil, "zlib unavailable"
        end
        return zlib.uncompress(string.sub(data, 17), usize), nil
    end
    return data, "not zlibbed (already raw)"
end

local function write_file(path, data)
    local f = io.open(path, "wb")
    if f == nil then
        log(string.format("[DBDump] cannot open for write: %s", path))
        return false
    end
    f:write(data)
    f:close()
    return true
end

local function on_read(ctx, filename, addr, len, total_size, offset)
    local name = basename(filename)
    if not TARGETS[name] then return end

    -- addr points into the game's own buffer, so copy the bytes out now
    local bytes = memory.read(addr, len)
    if bytes == nil then return end

    local t = chunks[name]
    if t == nil then t = {}; chunks[name] = t end
    t[#t + 1] = bytes

    if offset + len < total_size then return end   -- more to come

    local n = (seen[name] or 0) + 1
    seen[name] = n
    local full = table.concat(t)
    chunks[name] = nil

    local stem = string.format("%s.copy%d", string.gsub(name, "%.bin$", ""), n)
    write_file(outdir .. "\\" .. stem .. ".bin", full)

    local raw, note = unwrap(full)
    if raw == nil then
        log(string.format("[DBDump] %s copy %d from '%s': %d bytes, decompress failed (%s)",
            name, n, filename, #full, tostring(note)))
        return
    end
    write_file(outdir .. "\\" .. stem .. ".raw", raw)
    log(string.format("[DBDump] %s copy %d from '%s': %d bytes -> %d raw%s",
        name, n, filename, #full, #raw, note and ("  [" .. note .. "]") or ""))
end

function m.init(ctx)
    outdir = ctx.sider_dir .. "dbdump"
    ctx.register("livecpk_read", on_read)
    log("[DBDump] loaded. Waiting for the database files; output goes to " .. outdir)
end

return m
