#!/usr/bin/env python3
"""
Simple script to illuminate all Push2 buttons with white LEDs for development.
This makes it easier to read button labels.
"""

import time
import push2_python

def main():
    print("Initializing Push2...")

    # Initialize Push2
    push = push2_python.Push2()

    # Configure MIDI
    if not push.midi_is_configured():
        push.configure_midi()

    print("Setting all buttons to white...")

    # Set all buttons to white
    # Using the set_all_buttons_color method from the Push2 buttons interface
    push.buttons.set_all_buttons_color("white")

    print("All buttons illuminated white. Press Ctrl+C to exit.")

    try:
        # Keep the script running to maintain the illumination
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nTurning off buttons and exiting...")
        # Turn off all buttons when exiting
        push.buttons.set_all_buttons_color("black")
        print("Done.")

if __name__ == "__main__":
    main()
