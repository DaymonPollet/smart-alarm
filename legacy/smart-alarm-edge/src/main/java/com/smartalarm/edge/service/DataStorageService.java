package com.smartalarm.edge.service;

import com.smartalarm.edge.domain.SleepData;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.sql.Timestamp;

public class DataStorageService {
    // QuestDB PG wire protocol usually on 8812
    private static final String URL = "jdbc:postgresql://192.168.137.11:8812/qdb";
    private static final String USER = "admin";
    private static final String PASS = "Admin.1234";

    public DataStorageService() {
        try {
            Class.forName("org.postgresql.Driver");
            // Initialize table
            try (Connection conn = DriverManager.getConnection(URL, USER, PASS);
                 PreparedStatement stmt = conn.prepareStatement(
                     "CREATE TABLE IF NOT EXISTS sleep_data (" +
                     "ts TIMESTAMP, " +
                     "mean_hr DOUBLE, " +
                     "std_hr DOUBLE, " +
                     "sdnn DOUBLE, " +
                     "rmssd DOUBLE, " +
                     "min_hr DOUBLE, " +
                     "max_hr DOUBLE, " +
                     "mean_activity DOUBLE, " +
                     "std_activity DOUBLE) timestamp(ts) PARTITION BY DAY"
                 )) {
                stmt.execute();
                System.out.println("Connected to QuestDB and ensured table exists.");
            }
        } catch (Exception e) {
            System.err.println("QuestDB init failed: " + e.getMessage());
        }
    }

    public void storeRaw(SleepData data) {
        try (Connection conn = DriverManager.getConnection(URL, USER, PASS);
             PreparedStatement stmt = conn.prepareStatement(
                 "INSERT INTO sleep_data VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)")) {
            
            stmt.setTimestamp(1, new Timestamp(data.timestamp()));
            stmt.setDouble(2, data.meanHr());
            stmt.setDouble(3, data.stdHr());
            stmt.setDouble(4, data.sdnn());
            stmt.setDouble(5, data.rmssd());
            stmt.setDouble(6, data.minHr());
            stmt.setDouble(7, data.maxHr());
            stmt.setDouble(8, data.meanActivity());
            stmt.setDouble(9, data.stdActivity());
            
            stmt.execute();
        } catch (SQLException e) {
            System.err.println("Error storing data in QuestDB: " + e.getMessage());
        }
    }
}
