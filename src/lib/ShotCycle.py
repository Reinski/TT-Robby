# Copyright (c) 2023 Reiner Nikulski
# 
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
import sys
if 'micropython' not in sys.version.lower():
    from typing import List
import Shot

#DEFAULT_SHOT_VALUES = (0.0, 0.0, 0.5, 2.0) # must match the constructor parameters for Shot.Shot

class ShotCycle:
    """Defines a sequence of shots."""
    def __init__(self, shots: List[Shot.Shot]) -> None:
        self.shots = shots
        self.nextShotIndex = 0

    def get_next_shot(self) -> Shot.Shot:
        """Return the next shot from the sequence"""
        if self.nextShotIndex >= len(self.shots):
            self.nextShotIndex = 0
        shot = self.shots[self.nextShotIndex]
        self.nextShotIndex += 1
        return shot
    
    def reset(self) -> None:
        """Sets the next shot to the first one of the sequence"""
        self.nextShotIndex = 0

    def getStatusData(self) -> dict:
        return {
            'next_shot_index': self.nextShotIndex,
            'total_shots': len(self.shots),
            'pause_to_next_shot': self.shots[self.nextShotIndex].Pause
        }
    def getConfigData(self) -> dict:
        return {
            'shots': [s.getConfigData() for s in self.shots],
        }
