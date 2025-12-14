package com.smartalarm.cloud.model;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import lombok.Data;

@Data
@Entity
public class SleepSession {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    private Long sessionId;
    private double avgHr;
    private double avgHrv; // SDNN
    private double totalSleepTime; // minutes
    private double deepSleepPercentage;
    private double remSleepPercentage;
    private double lightSleepPercentage;
    private int awakeCount;
}
