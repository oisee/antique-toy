Conrado Badenas, [2026-02-24 15:24]

## RET cc T-state counting error in Ch.2 DOWN_HL

Section "DOWN_HL: Moving One Pixel Row Down" in Chapter 2 has mistakes in T-state
counting for `RET cc` instructions:
- RET cc taken (condition true) = **11 T-states**
- RET cc not taken (condition false) = **5 T-states**

The comments in the code have the 5/11 figures in reverse order, and the cycle
counting is affected by this. The conclusion about which variant is faster is still
valid, but the numbers need correcting.

Action items:
1. Fix RET cc T-state comments in Ch.2 DOWN_HL section (swap 5↔11)
2. Recalculate total cycle counts for both paths
3. Verify with automated T-state counting tool (spectools/)
4. Update all 4 language editions
