--[[
Map 3 joystick buttons to ArduSub RNG_HOLD (surftrak) functions.

See the README.md file for parameter settings.
]]--

function update()
  local action_target_cm = param:get('SCR_USER1')
  if action_target_cm == nil then
    gcs:send_text(6, "rng_hold_buttons.lua: set SCR_USER1 to rangefinder target, in cm")
    return update, 10000
  end

  if action_target_cm < 100 then
    gcs:send_text(6, "rng_hold_buttons.lua: SCR_USER1 must be 100 (1m) or more")
    return update, 10000
  end

  local action_inc_cm = param:get('SCR_USER2')
  if action_inc_cm == nil then
    gcs:send_text(6, "rng_hold_buttons.lua: set SCR_USER2 to rangefinder target increment value, in cm")
    return update, 10000
  end

  if action_inc_cm < 1 then
    gcs:send_text(6, "rng_hold_buttons.lua: SCR_USER2 must be 1 (1cm) or more")
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

  local idx_set_target = 1
  local idx_inc = 2
  local idx_dec = 3

  -- Set target
  if count[idx_set_target] > 0 then
    sub:set_rangefinder_target_cm(action_target_cm)
  end

  -- Increment or decrement
  local net_inc = count[idx_inc] - count[idx_dec]
  if net_inc ~= 0 then
    local curr_target_cm = sub:get_rangefinder_target_cm()
    local next_target_cm = curr_target_cm + net_inc * action_inc_cm
    if next_target_cm < 80 then
      gcs:send_text(6, "rng_hold_buttons.lua: lower limit is 80cm")
      next_target_cm = 80
    end
    sub:set_rangefinder_target_cm(next_target_cm)
  end

  return update, 200
end

return update(), 200
