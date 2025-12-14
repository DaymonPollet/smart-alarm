package com.smartalarm.cloud.model;

import lombok.Data;

@Data
public class SleepSession {
    private Long sessionId;
    private double avgHr;
    private double avgHrv; // SDNN
    private double totalSleepTime; // minutes
    private double deepSleepPercentage;
    private double remSleepPercentage;
    private double lightSleepPercentage;
    private int awakeCount;
}
