package com.smartalarm.edge;

import com.smartalarm.edge.service.*;

public class AppContext {
    private static AppContext instance;
    
    private FitbitService fitbitService;
    private LocalModelService localModelService;
    private AzureService azureService;
    private DataStorageService dataStorageService;
    private CloudSyncService cloudSyncService;

    private AppContext() {
        // Initialize services
        fitbitService = new FitbitService();
        
        String modelUrl = System.getenv("MODEL_SERVICE_URL");
        if (modelUrl == null) modelUrl = "http://192.168.137.11:30000/predict";
        localModelService = new LocalModelService(modelUrl);
        
        azureService = new AzureService(System.out::println);
        dataStorageService = new DataStorageService();
        
        String cloudUrl = System.getenv("CLOUD_SERVICE_URL");
        if (cloudUrl == null) cloudUrl = "https://smart-alarm-cloud.grayforest-c8a2cdd5.northeurope.azurecontainerapps.io/predict"; 
        cloudSyncService = new CloudSyncService(cloudUrl);
    }

    public static synchronized AppContext getInstance() {
        if (instance == null) {
            instance = new AppContext();
        }
        return instance;
    }

    public FitbitService getFitbitService() { return fitbitService; }
    public LocalModelService getLocalModelService() { return localModelService; }
    public AzureService getAzureService() { return azureService; }
    public DataStorageService getDataStorageService() { return dataStorageService; }
    public CloudSyncService getCloudSyncService() { return cloudSyncService; }
}
