package com.smartalarm.edge.domain;

public value record SleepData(
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
}
