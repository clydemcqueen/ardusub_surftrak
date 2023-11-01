--[[
Map 3 joystick buttons to ArduSub RNG_HOLD (surftrak) functions.

param set SCR_USER1 500   # Rangefinder target, in cm
param set SCR_USER2 10    # Rangefinder target increment / decrement amount, in cm

param set BTN0_SFUNCTION  108   # XBox controller shift-A: set target to SCR_USER1
param set BTN1_SFUNCTION  109   # XBox controller shift-B: increment target by SCR_USER2
param set BTN2_SFUNCTION  110   # XBox controller shift-X: decrement target by SCR_USER2

Handy parameters for SITL testing:
param set RNGFND1_MAX_CM 4000
param set RNGFND1_MIN_CM 50
param set RNGFND_PID_P 0.12
param set RNGFND_PID_I 0.03
param set RNGFND_PID_D 0.3
]]--

function update()
  local target_cm = param:get('SCR_USER1')
  if (target_cm == nil) or (target_cm <= 0) then
    gcs:send_text(6, "rng_hold_buttons.lua: set SCR_USER1 to rangefinder target, in cm")
    return update, 10000
  end

  local inc_cm = param:get('SCR_USER2')
  if (inc_cm == nil) or (inc_cm <= 0) then
    gcs:send_text(6, "rng_hold_buttons.lua: set SCR_USER2 to rangefinder target increment value, in cm")
    return update, 10000
  end

  -- Get and clear button counts
  local count = {}
  for i = 1, 3 do
    count[i] = sub:get_and_clear_button_count(i)
  end

  -- Ignore buttons if the rangefinder is unhealthy
  for i = 1, 3 do
    if count[i] > 0 and not sub:rangefinder_alt_ok() then
      gcs:send_text(6, "rng_hold_buttons.lua: rangefinder not ok, ignoring buttons")
      return update, 200
    end
  end

  local btn_set_target = 1
  local btn_inc = 2
  local btn_dec = 3

  -- Set target
  if count[btn_set_target] > 0 then
    sub:set_target_rangefinder_cm(target_cm)
  end

  -- Increment or decrement
  local net_inc = count[btn_inc] - count[btn_dec]
  if net_inc ~= 0 then
    target = sub:get_target_rangefinder_cm()
    sub:set_target_rangefinder_cm(target + net_inc * inc_cm)
  end

  return update, 200
end

return update(), 200
