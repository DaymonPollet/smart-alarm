package com.smartalarm.cloud.service;

import com.smartalarm.cloud.model.SleepSession;
import org.springframework.stereotype.Service;

@Service
public class AnomalyDetectionService {

    /**
     * Cloud AI Model: Detects anomalies in sleep patterns.
     * This represents the "Cloud AI" requirement.
     * 
     * Logic:
     * - Low HRV (High Stress)
     * - Low Deep Sleep (Poor Recovery)
     * - High Resting HR (Potential Illness)
     */
    public String analyze(SleepSession session) {
        StringBuilder report = new StringBuilder("Sleep Analysis Report:\n");
        boolean anomalyFound = false;

        // 1. HRV Check (SDNN < 20ms is concerning)
        if (session.getAvgHrv() < 20) {
            report.append("- WARNING: Very low HRV detected. High stress or poor recovery.\n");
            anomalyFound = true;
        }

        // 2. Deep Sleep Check (< 10% is low)
        if (session.getDeepSleepPercentage() < 10) {
            report.append("- WARNING: Insufficient Deep Sleep. You may feel groggy.\n");
            anomalyFound = true;
        }

        // 3. Resting HR Check (> 80 bpm resting is high for most)
        if (session.getAvgHr() > 80) {
            report.append("- WARNING: Elevated Resting Heart Rate. Check for illness or overtraining.\n");
            anomalyFound = true;
        }

        if (!anomalyFound) {
            report.append("- All metrics within normal range. Good sleep!\n");
        }

        return report.toString();
    }
}
