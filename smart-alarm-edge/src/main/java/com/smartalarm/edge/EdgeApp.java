package com.smartalarm.edge;

import javafx.application.Application;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.Scene;
import javafx.scene.control.Button;
import javafx.scene.control.Label;
import javafx.scene.layout.BorderPane;
import javafx.scene.layout.HBox;
import javafx.scene.layout.VBox;
import javafx.stage.Stage;

public class EdgeApp extends Application {

    @Override
    public void start(Stage primaryStage) {
        BorderPane root = new BorderPane();
        root.getStyleClass().add("root");

        // Navbar
        HBox navbar = new HBox();
        navbar.getStyleClass().add("navbar");
        navbar.setAlignment(Pos.CENTER_LEFT);
        Label logo = new Label("Smart Alarm");
        logo.getStyleClass().add("header-label");
        logo.setStyle("-fx-font-size: 24px;");
        navbar.getChildren().add(logo);
        root.setTop(navbar);

        // Center Content
        VBox center = new VBox(20);
        center.setAlignment(Pos.CENTER);
        center.setPadding(new Insets(50));

        Label title = new Label("Sleep Well, Wake Up Merry");
        title.getStyleClass().add("header-label");

        Label subtitle = new Label("AI-Powered Smart Alarm System");
        subtitle.getStyleClass().add("sub-header-label");

        // Status Indicator
        HBox statusBox = new HBox(10);
        statusBox.setAlignment(Pos.CENTER);
        Label statusDot = new Label();
        statusDot.getStyleClass().add("status-indicator");
        Label statusText = new Label("System Active");
        statusBox.getChildren().addAll(statusDot, statusText);

        // Buttons
        HBox buttonBox = new HBox(20);
        buttonBox.setAlignment(Pos.CENTER);
        Button startBtn = new Button("Start Sleep Tracking");
        startBtn.getStyleClass().add("button");
        startBtn.getStyleClass().add("button-accent");
        
        startBtn.setOnAction(e -> {
            CloudClient client = new CloudClient();
            com.smartalarm.shared.SleepData data = new com.smartalarm.shared.SleepData();
            data.setHeartRate(72);
            data.setMovementLevel(0.9);
            data.setSleepStage("LIGHT");
            data.setTimestamp(java.time.LocalDateTime.now());
            data.setUserId("user-1");
            
            String result = client.sendData(data);
            System.out.println("Cloud Analysis: " + result);
        });

        Button configBtn = new Button("Configure Alarm");
        configBtn.getStyleClass().add("button");

        buttonBox.getChildren().addAll(startBtn, configBtn);

        // Feature Cards
        HBox cards = new HBox(20);
        cards.setAlignment(Pos.CENTER);
        cards.getChildren().addAll(
                createCard("Local AI", "Edge processing on Pi"),
                createCard("Cloud Sync", "Data stored securely"),
                createCard("Smart Wake", "Wake up refreshed")
        );

        center.getChildren().addAll(title, subtitle, statusBox, buttonBox, cards);
        root.setCenter(center);

        Scene scene = new Scene(root, 1000, 700);
        scene.getStylesheets().add(getClass().getResource("/css/christmas.css").toExternalForm());

        primaryStage.setTitle("Smart Alarm - Christmas Edition");
        primaryStage.setScene(scene);
        primaryStage.show();
    }

    private VBox createCard(String title, String desc) {
        VBox card = new VBox(10);
        card.getStyleClass().add("card");
        card.setPrefWidth(200);
        card.setAlignment(Pos.CENTER);

        Label t = new Label(title);
        t.setStyle("-fx-font-weight: bold; -fx-font-size: 16px; -fx-text-fill: #006400;");
        Label d = new Label(desc);
        d.setWrapText(true);

        card.getChildren().addAll(t, d);
        return card;
    }

    public static void main(String[] args) {
        launch(args);
    }
}
