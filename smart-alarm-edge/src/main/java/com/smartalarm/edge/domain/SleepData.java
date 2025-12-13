package com.smartalarm.edge.domain;

public value record SleepData(
    double meanHr,
    double stdHr,
    double minHr,
    double maxHr,
    double meanActivity,
    double stdActivity,
    long timestamp
) {
    public SleepData(double meanHr, double stdHr, double minHr, double maxHr, double meanActivity, double stdActivity) {
        this(meanHr, stdHr, minHr, maxHr, meanActivity, stdActivity, System.currentTimeMillis());
    }
}
