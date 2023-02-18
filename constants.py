import os
from pynput.keyboard import Key

# repo path
root_path = os.path.dirname(os.path.abspath(__file__))

# socket information
ip = '127.0.0.1'
port = 12350

# data format
packet_format = 'fh4'

# default car config
example_car_ordinal = 'example'

# === UI settings ===
background_color = "#1a181a"
text_color = "#a1a1a1"

# === short-cut ===
stop = Key.pause # stop program
close = Key.end # close program
analysis = Key.f8
reset = Key.f7
gatherratios = Key.f9
collect_data = Key.f10
writeback = Key.f11
