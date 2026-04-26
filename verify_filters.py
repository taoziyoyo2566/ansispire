
import sys
import os

# Add project root to path to find filter_plugins
sys.path.append(os.getcwd())

from filter_plugins.custom_filters import ljust, rjust

test_val = "hello"
l_result = ljust(test_val, 10)
r_result = rjust(test_val, 10)

print(f"'{l_result}' (len: {len(l_result)})")
print(f"'{r_result}' (len: {len(r_result)})")

if l_result == "hello     " and r_result == "     hello":
    print("SUCCESS")
else:
    print("FAILURE")
    sys.exit(1)
