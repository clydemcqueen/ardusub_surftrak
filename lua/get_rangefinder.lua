-- Set the RANGEFINDER stream rate so QGroundControl 4.2.8 can display the rf widget.
--
-- Problem: older versions of QGC (e.g., 4.2.8) depend on RANGEFINDER messages to display the rf widget. As of ArduSub
-- 4.7 these are no longer part of the "extra 3" messages, so the widget won't work.
--
-- Reference: https://github.com/ArduPilot/ardupilot/pull/31095

local RANGEFINDER_MSG = uint32_t(173)

function update() -- this is the loop which periodically runs
  gcs:set_message_interval(0, RANGEFINDER_MSG, math.floor(1000000 / 2))
  return update, 5000 -- every 5 seconds
end

gcs:send_text(6, "get_rangefinder.lua: loaded")
return update()
