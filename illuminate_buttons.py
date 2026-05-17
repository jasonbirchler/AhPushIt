#!/usr/bin/env python3
"""
Simple script to illuminate all Push2 buttons for development.
RGB-capable buttons are lit orange; black-and-white-only buttons stay white.
This makes it easier to read button labels.
"""

import sys
import time
import push2_python

def main():
    print("Initializing Push2...")

    # Initialize Push2
    push = push2_python.Push2()

    # Push2.__init__ configures MIDI in only (skip_midi_out=True).
    # Configure MIDI out directly so that MIDI OUT is available before we
    # try to set LED colours.
    if push.midi_out_port is None:
        print("Configuring MIDI out...")
        try:
            push.configure_midi_out()
        except push2_python.exceptions.Push2MIDIeviceNotFound as e:
            print(f"ERROR: Could not find Push2 MIDI out port: {e}")
            print("Is the Push2 connected and powered on?")
            sys.exit(1)

    if not push.midi_is_configured():
        print("ERROR: MIDI is not fully configured (midi_out_port is None).")
        sys.exit(1)

    # Give the Push2 device a brief moment to settle after the MIDI out
    # port is opened so that the first CC messages arrive cleanly.
    time.sleep(0.1)

    print("MIDI configured. Output port:", push.midi_out_port)
    print("Setting RGB buttons to orange and BW buttons to white...")

    # Set each button individually based on whether it supports RGB colours.
    # RGB-capable buttons get a warm orange so they stand out clearly from
    # the black-and-white-only buttons, which stay white.
    rgb_color  = "green"
    bw_color   = "white"
    for button_number, button_info in push.buttons.button_map.items():
        color = rgb_color if button_info.get("Color") else bw_color
        push.buttons.set_button_color(button_info["Name"], color)

    print("All buttons illuminated (RGB=orange, BW=white). Press Ctrl+C to exit.")

    try:
        # Keep the script running to maintain the illumination
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nTurning off buttons and exiting...")
        # Turn off all RGB buttons to black; BW buttons back to black too
        for button_number, button_info in push.buttons.button_map.items():
            push.buttons.set_button_color(button_info["Name"], "black")
        print("Done.")

if __name__ == "__main__":
    main()
