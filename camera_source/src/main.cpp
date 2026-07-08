#include "utils/logger.hpp"
#include "utils/config_loader.hpp"
#include "media/stream.hpp"
#include "media/tcp_client.hpp"
#include "control/TmcDriver.hpp"
#include "control/lens_controller.hpp"

#include <iostream>
#include <thread>
#include <atomic>
#include <csignal>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <sstream>

#define TAG "Main"

std::atomic<bool> g_running(true);
std::shared_ptr<LensController> g_lens_controller = nullptr;

void signal_handler(int signum) {
    Logger::info(TAG, "Interrupt signal received. Shutting down...");
    g_running = false;
}

// UDP command listener thread for lens/motor controls
void udp_command_listener(int port) {
    Logger::info(TAG, "Starting UDP command listener on port " + std::to_string(port) + "...");
    
    int sock_fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock_fd < 0) {
        Logger::error(TAG, "Failed to create UDP socket.");
        return;
    }

    sockaddr_in serv_addr{};
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_addr.s_addr = INADDR_ANY;
    serv_addr.sin_port = htons(port);

    if (bind(sock_fd, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) < 0) {
        Logger::error(TAG, "Failed to bind UDP socket to port " + std::to_string(port));
        close(sock_fd);
        return;
    }

    char buffer[256];
    sockaddr_in cli_addr{};
    socklen_t cli_len = sizeof(cli_addr);

    struct timeval tv;
    tv.tv_sec = 1;
    tv.tv_usec = 0;
    setsockopt(sock_fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

    while (g_running) {
        memset(buffer, 0, sizeof(buffer));
        ssize_t len = recvfrom(sock_fd, buffer, sizeof(buffer) - 1, 0, (struct sockaddr*)&cli_addr, &cli_len);
        
        if (len > 0) {
            std::string cmd(buffer);
            // Trim whitespace
            cmd.erase(cmd.find_last_not_of(" \t\r\n") + 1);
            Logger::info(TAG, "Received UDP Command: " + cmd);

            if (!g_lens_controller) {
                Logger::warn(TAG, "Lens controller not initialized. Command ignored.");
                continue;
            }

            // Command parsing logic
            if (cmd == "CALIB") {
                g_lens_controller->calibrate();
            } 
            else if (cmd.rfind("ZOOM:", 0) == 0) { // Starts with "ZOOM:"
                try {
                    int steps = std::stoi(cmd.substr(5));
                    g_lens_controller->zoom_step(steps);
                } catch (...) {
                    Logger::error(TAG, "Invalid ZOOM command syntax.");
                }
            } 
            else if (cmd.rfind("FOCUS:", 0) == 0) { // Starts with "FOCUS:"
                try {
                    int steps = std::stoi(cmd.substr(6));
                    g_lens_controller->focus_step(steps);
                } catch (...) {
                    Logger::error(TAG, "Invalid FOCUS command syntax.");
                }
            }
            else if (cmd.rfind("IRIS:", 0) == 0) { // Starts with "IRIS:"
                try {
                    int pos = std::stoi(cmd.substr(5));
                    g_lens_controller->iris_to(pos);
                } catch (...) {
                    Logger::error(TAG, "Invalid IRIS command syntax.");
                }
            }
            else {
                Logger::warn(TAG, "Unknown command: " + cmd);
            }
        }
    }

    close(sock_fd);
    Logger::info(TAG, "UDP command listener thread stopped.");
}

int main(int argc, char* argv[]) {
    // 1. Register signal handlers
    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);

    Logger::info(TAG, "--- Custom CV25 IP Camera Daemon Starting ---");

    // 2. Load settings
    CameraConfig config;
    std::string config_path = "config/camera_config.json";
    if (argc > 1) {
        config_path = argv[1];
    }
    ConfigLoader::load(config_path, config);

    // 3. Initialize Stepper Motor Controller
    auto tmc_drv = TmcDriver::create(config.tmc_dev);
    if (tmc_drv) {
        g_lens_controller = std::make_shared<LensController>(tmc_drv);
        Logger::info(TAG, "Motor drivers initialized successfully.");
    } else {
        Logger::warn(TAG, "Could not load tmc_driver. Motor controls disabled.");
    }

    // 4. Start GStreamer Capture Stream
    Stream stream(config.resolution, config.framerate);
    if (!stream.start()) {
        Logger::error(TAG, "Failed to start camera capture stream. Exiting.");
        return -1;
    }

    // 5. Start TCP client for Raspberry Pi YOLO Server
    TcpClient tcp_client(config.pi_ip, config.pi_port);

    // 6. Spawn UDP listener thread on port 8080 for lens commands
    std::thread cmd_thread(udp_command_listener, 8080);

    // 7. Main capture and transmission loop
    Logger::info(TAG, "Core processing loop active.");
    cv::Mat frame;
    while (g_running) {
        if (stream.get_frame(frame)) {
            if (!tcp_client.send_frame(frame)) {
                // If send failed, sleep a bit to avoid connection flood log spam
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
            }
        } else {
            // Wait brief moment if no frame is returned
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
    }

    // 8. Cleanup and shutdown
    Logger::info(TAG, "Stopping services...");
    stream.stop();
    tcp_client.disconnect();

    if (cmd_thread.joinable()) {
        cmd_thread.join();
    }

    Logger::info(TAG, "--- Custom CV25 IP Camera Daemon Halted ---");
    return 0;
}
