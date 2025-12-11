package com.smartalarm.edge;

import com.smartalarm.shared.SleepData;

public class LocalModelService {

    public String predictWakeUpTime(SleepData currentData) {
        double hr = currentData.getHeartRate();
        double movement = currentData.getMovementLevel();

        if (movement > 0.8 && hr > 75) {
            return "WAKE_UP_NOW";
        }
        
        if (currentData.getSleepStage().equalsIgnoreCase("LIGHT")) {
            return "PREPARE_TO_WAKE";
        }

        return "WAIT";
    }
}
