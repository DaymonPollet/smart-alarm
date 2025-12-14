package com.smartalarm.edge.domain;

/**
 * Represents a 30-second epoch of sleep data features.
 * Features are engineered to match Fitbit API capabilities:
 * - HR/HRV from 1sec resolution Heart Rate API.
 * - Activity from 1min resolution Steps/Activity API.
 */
public record SleepData(
    double meanHr,
    double stdHr,
    double sdnn,
    double rmssd,
    double minHr,
    double maxHr,
    double meanActivity,
    double stdActivity,
    long timestamp
) {
    public SleepData(double meanHr, double stdHr, double sdnn, double rmssd, double minHr, double maxHr, double meanActivity, double stdActivity) {
        this(meanHr, stdHr, sdnn, rmssd, minHr, maxHr, meanActivity, stdActivity, System.currentTimeMillis());
    }
    
    // Helper to calculate Heart Rate (BPM) for legacy code compatibility
    public double heartRate() {
        return meanHr;
    }
}
