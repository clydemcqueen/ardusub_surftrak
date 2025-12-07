--[[
    Use GUIDED mode with ABOVE_TERRAIN frame to run transects at a constant distance above the seafloor

    Requirements:
    * Good positioning system, typically a DVL
    * Down-facing rangefinder, typically the same DVL

    Typical operation:
    * Dive to the start of the transect, at the target distance off the seafloor
    * Enter GUIDED mode, the ROV will maintain a constant forward speed and a constant distance above the seafloor
    * If an obstacle appears the pilot can fly around it while maintaining seafloor distance and speed
    * The pilot can exit GUIDED mode at any time; when the pilot re-enters GUIDED mode the script will resume

    The rangefinder target is set the first time the ROV enters GUIDED mode. The pilot can increment or decrement the
    target using joystick buttons. If the pilot enters SURFTRAK mode the rangefinder target is unset.

    The forward speed is controlled by the WPNAV_SPEED parameter. The pilot can increment or decrement the parameter
    using joystick buttons, but note that changes will not register until the next time the pilot enters GUIDED mode.

    Troubleshooting:
    * Too close to the surface? The ROV must be below SURFTRAK_DEPTH
    * Too far away from the seafloor? Check RNGFND1_MAX

    Example joystick button settings:
    param set BTN0_FUNCTION    1.0         # shift
    param set BTN11_SFUNCTION  108         # shift-dpad-up      script_1: increment rf_target by 10 cm
    param set BTN12_SFUNCTION  109         # shift-dpad-down    script_2: decrement rf_target by 10 cm
    param set BTN13_SFUNCTION  111         # shift-dpad-right   script_4: increment speed by 10 cm/s
    param set BTN14_SFUNCTION  110         # shift-dpad-left    script_3: decrement speed by 10 cm/s
    param set BTN2_SFUNCTION   11          # shift-X            GUIDED mode

]]--

local SURFTRAK_DEPTH = Parameter()
local WPNAV_SPEED = Parameter()
if not SURFTRAK_DEPTH:init('SURFTRAK_DEPTH') or not WPNAV_SPEED:init('WPNAV_SPEED') then
    gcs:send_text(3, "transect.lua: parameters missing, exit")
    return
end

local WARMUP_TIME_MS = 5000     -- update time as EKF is warming up
local UPDATE_TIME_MS = 100      -- update time
local RF_TIMEOUT_MS = 2000      -- timeout for rangefinder_alt_ok() to be false before stopping
local FUTURE_S = 10             -- target is a point along the heading, distance = speed * FUTURE_S

local GUIDED_MODE_NUM = 4       -- sub GUIDED mode number
local SURFTRAK_MODE_NUM = 21    -- sub SURFTRAK mode number
local ROTATION_PITCH_270 = 25   -- down-facing

local SPEED_INC_CMS = 10        -- inc / dec WPNAV_SPEED by this amount per button press
local SPEED_MIN_CMS = 10
local SPEED_MAX_CMS = 150

local RF_TARGET_INC = 0.1       -- inc / dec rf_target by this amount per button press
local RF_TARGET_MIN = 0.5
local RF_TARGET_MAX = 50.0

local BTN_INC_RF_TARGET = 1     -- joystick script button assignments
local BTN_DEC_RF_TARGET = 2     -- Lua indices 1..4 map to joystick button functions 108..111
local BTN_INC_SPEED = 3
local BTN_DEC_SPEED = 4

local rf_target                 -- rangefinder target
local running = false           -- if true, we are running the update loop at 10Hz
local in_control = false        -- if true, we are sending posvel targets at 10Hz
local rf_healthy_ms             -- last good rangefinder reading

local function clamp(val, min, max)
    if val < min then return min end
    if val > max then return max end
    return val
end

local function set_rf_target(proposed_rf_target)
    -- Round the proposed target to the nearest 0.1m, this helps the pilot set specific targets
    rf_target = clamp(math.floor(proposed_rf_target * 10 + 0.5) / 10, RF_TARGET_MIN, RF_TARGET_MAX)
    gcs:send_text(6, string.format("transect.lua: set rangefinder target to %.2f m", rf_target))
end

local function respond_to_joystick_buttons()
    -- Get and clear button counts
    local count = {}
    for i = 1, 4 do
        count[i] = sub:get_and_clear_button_count(i)
    end

    -- Increment or decrement WPNAV_SPEED
    -- Changes take effect the next time the pilot enters GUIDED mode
    local net_inc = count[BTN_INC_SPEED] - count[BTN_DEC_SPEED]
    if net_inc ~= 0 then
        WPNAV_SPEED:set(clamp(WPNAV_SPEED:get() + net_inc * SPEED_INC_CMS, SPEED_MIN_CMS, SPEED_MAX_CMS))
        gcs:send_text(6, string.format("transect.lua: change WPNAV_SPEED to %.0f cms", WPNAV_SPEED:get()))
    end

    if rf_target == nil then
        return
    end

    -- Increment or decrement rf_target
    net_inc = count[BTN_INC_RF_TARGET] - count[BTN_DEC_RF_TARGET]
    if net_inc ~= 0 then
        set_rf_target(rf_target + net_inc * RF_TARGET_INC)
    end
end

local function set_posvel_target(pos)
    -- Do not try to set the target if the rangefinder is unhealthy to avoid spamming the pilot
    -- The rangefinder may time out every 10s, see https://github.com/bluerobotics/BlueOS-Water-Linked-DVL/issues/44
    if not sub:rangefinder_alt_ok() then
        return
    end

    local vel_fwd = WPNAV_SPEED:get() * 0.01
    local heading = ahrs:get_yaw_rad()

    -- project forward along heading to calc target xy position
    local dist = vel_fwd * FUTURE_S
    local target_pos = Vector3f()
    target_pos:x(pos:x() + dist * math.cos(heading))
    target_pos:y(pos:y() + dist * math.sin(heading))
    target_pos:z(rf_target)

    local target_vel = Vector3f()
    target_vel:x(vel_fwd * math.cos(heading))
    target_vel:y(vel_fwd * math.sin(heading))
    target_vel:z(0)

    if not vehicle:set_target_posvel_terrain(target_pos, target_vel) then
        gcs:send_text(3, "transect.lua: failed to set target posvel")
    end
end

local function update()
    respond_to_joystick_buttons()

    local pos = ahrs:get_relative_position_NED_origin()
    if pos == nil then
        -- Wait for EKF to warm up
        running = false
        -- gcs:send_text(6, string.format("transect.lua: wait for EKF to warm up"))
        return update, WARMUP_TIME_MS
    end

    if not running then
        running = true
        gcs:send_text(6, string.format("transect.lua: main loop running"))
    end

    -- Convert cm above origin to NED (m below origin)
    local surftrak_depth = -SURFTRAK_DEPTH:get() * 0.01

    if arming:is_armed() and vehicle:get_mode() == GUIDED_MODE_NUM and pos:z() >= surftrak_depth then
        -- A good rangefinder reading is required to initialize the rangefinder target and take control
        if sub:rangefinder_alt_ok() then
            rf_healthy_ms = millis()
            
            if rf_target == nil then
                set_rf_target(rangefinder:distance_orient(ROTATION_PITCH_270))
            end

            if not in_control then
                gcs:send_text(6, string.format("transect.lua: moving forward at %.0f cms", WPNAV_SPEED:get()))
                in_control = true
            end
        else
            -- Rangefinder is not healthy
            if in_control then
                if millis() - rf_healthy_ms > RF_TIMEOUT_MS then
                    gcs:send_text(3, "transect.lua: rangefinder timeout, stopping")
                    in_control = false
                end
            end
        end

        if in_control then
            set_posvel_target(pos)
        end

    else -- disarmed, wrong mode, too close to the surface
        if in_control then
            gcs:send_text(6, "transect.lua: stopping")
            in_control = false
        end
    end

    -- If the pilot enters SURFTRAK mode, unset rf_target
    if rf_target ~= nil and vehicle:get_mode() == SURFTRAK_MODE_NUM then
        gcs:send_text(6, "transect.lua: forget the old rangefinder target")
        rf_target = nil
    end

    return update, UPDATE_TIME_MS
end

gcs:send_text(6,"transect.lua loaded")

return update()
