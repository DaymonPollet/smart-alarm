package com.smartalarm.edge.service;

import com.smartalarm.edge.AppContext;
import com.smartalarm.edge.domain.FitbitPacket;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.io.InputStream;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.stream.Collectors;

public class WebServerService {
    private HttpServer server;
    private final int port = 8080;

    public void start() {
        try {
            server = HttpServer.create(new InetSocketAddress(port), 0);
            server.createContext("/", new StaticHandler());
            server.createContext("/api/status", new StatusHandler());
            server.createContext("/api/config", new ConfigHandler());
            server.setExecutor(null);
            server.start();
            System.out.println("Web Server started on port " + port);
        } catch (IOException e) {
            System.err.println("Failed to start Web Server: " + e.getMessage());
        }
    }

    public void stop() {
        if (server != null) {
            server.stop(0);
        }
    }

    static class StaticHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange t) throws IOException {
            String path = t.getRequestURI().getPath();
            if ("/".equals(path) || "/index.html".equals(path)) {
                serveResource(t, "/web/index.html", "text/html");
            } else {
                String response = "404 Not Found";
                t.sendResponseHeaders(404, response.length());
                OutputStream os = t.getResponseBody();
                os.write(response.getBytes());
                os.close();
            }
        }

        private void serveResource(HttpExchange t, String resourcePath, String contentType) throws IOException {
            InputStream is = getClass().getResourceAsStream(resourcePath);
            if (is == null) {
                String response = "404 Not Found (Resource)";
                t.sendResponseHeaders(404, response.length());
                OutputStream os = t.getResponseBody();
                os.write(response.getBytes());
                os.close();
                return;
            }
            
            String content = new BufferedReader(new InputStreamReader(is, StandardCharsets.UTF_8))
                    .lines().collect(Collectors.joining("\n"));
            
            byte[] bytes = content.getBytes(StandardCharsets.UTF_8);
            t.getResponseHeaders().set("Content-Type", contentType);
            t.sendResponseHeaders(200, bytes.length);
            OutputStream os = t.getResponseBody();
            os.write(bytes);
            os.close();
        }
    }

    static class StatusHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange t) throws IOException {
            AppContext ctx = AppContext.getInstance();
            boolean fitbitEnabled = ctx.getFitbitService().isEnabled();
            
            String json = String.format("{\"fitbit_enabled\": %b, \"status\": \"running\"}", fitbitEnabled);
            
            t.getResponseHeaders().set("Content-Type", "application/json");
            t.sendResponseHeaders(200, json.length());
            OutputStream os = t.getResponseBody();
            os.write(json.getBytes());
            os.close();
        }
    }

    static class ConfigHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange t) throws IOException {
            if ("POST".equals(t.getRequestMethod())) {
                InputStreamReader isr = new InputStreamReader(t.getRequestBody(), StandardCharsets.UTF_8);
                BufferedReader br = new BufferedReader(isr);
                String body = br.lines().collect(Collectors.joining());
                
                AppContext ctx = AppContext.getInstance();
                if (body.contains("\"fitbit_enabled\": true")) {
                    ctx.getFitbitService().setEnabled(true);
                } else if (body.contains("\"fitbit_enabled\": false")) {
                    ctx.getFitbitService().setEnabled(false);
                }
                
                String response = "{\"status\": \"updated\"}";
                t.getResponseHeaders().set("Content-Type", "application/json");
                t.sendResponseHeaders(200, response.length());
                OutputStream os = t.getResponseBody();
                os.write(response.getBytes());
                os.close();
            } else {
                t.sendResponseHeaders(405, -1); // Method Not Allowed
            }
        }
    }
}
