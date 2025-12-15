package com.smartalarm.edge;

import com.smartalarm.edge.ui.fx.SmartAlarmController;
import javafx.application.Application;
import javafx.fxml.FXMLLoader;
import javafx.scene.Parent;
import javafx.scene.Scene;
import javafx.stage.Stage;

import java.io.IOException;

public class App extends Application {

    private SmartAlarmController controller;

    @Override
    public void start(Stage stage) throws IOException {
        // Start Web Server
        com.smartalarm.edge.service.WebServerService webServer = new com.smartalarm.edge.service.WebServerService();
        webServer.start();

        FXMLLoader fxmlLoader = new FXMLLoader(App.class.getResource("/view/smart-alarm.fxml"));
        Parent root = fxmlLoader.load();
        controller = fxmlLoader.getController();
        
        Scene scene = new Scene(root, 800, 600);
        scene.getStylesheets().add(getClass().getResource("/styles.css").toExternalForm());
        
        stage.setTitle("Smart Alarm Edge Dashboard");
        stage.setScene(scene);
        stage.show();
    }

    @Override
    public void stop() throws Exception {
        if (controller != null) {
            controller.stop();
        }
        super.stop();
    }

    public static void main(String[] args) {
        if (args.length > 0 && args[0].equals("--headless")) {
            System.out.println("Starting in Headless Mode...");
            // Initialize Context
            com.smartalarm.edge.AppContext.getInstance();
            
            // Start Web Server
            com.smartalarm.edge.service.WebServerService webServer = new com.smartalarm.edge.service.WebServerService();
            webServer.start();
            
            // Start Monitoring
            com.smartalarm.edge.service.MonitoringService monitor = new com.smartalarm.edge.service.MonitoringService(System.out::println);
            monitor.start();
            
            // Keep alive
            try {
                Thread.currentThread().join();
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        } else {
            launch();
        }
    }
}
