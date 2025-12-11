package com.smartalarm.shared;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class SleepData {
    private String userId;
    private LocalDateTime timestamp;
    private double heartRate;
    private double movementLevel;
    private String sleepStage;
}
