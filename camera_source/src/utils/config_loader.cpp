#include "config_loader.hpp"
#include "logger.hpp"
#include <fstream>
#include <algorithm>

#define TAG "ConfigLoader"

static std::string trim(const std::string& str) {
    size_t first = str.find_first_not_of(" \t\r\n'\"");
    if (first == std::string::npos) return "";
    size_t last = str.find_last_not_of(" \t\r\n'\"");
    return str.substr(first, (last - first + 1));
}

bool ConfigLoader::load(const std::string& path, CameraConfig& config) {
    std::ifstream file(path);
    if (!file.is_open()) {
        Logger::warn(TAG, "Config file not found at: " + path + ". Using default settings.");
        return false;
    }

    std::string line;
    while (std::getline(file, line)) {
        size_t colon = line.find(':');
        if (colon == std::string::npos) continue;

        std::string key = trim(line.substr(0, colon));
        std::string val_part = line.substr(colon + 1);
        
        // Remove trailing comma if present
        size_t comma = val_part.find_last_of(',');
        if (comma != std::string::npos) {
            val_part = val_part.substr(0, comma);
        }
        std::string val = trim(val_part);

        if (key == "pi_ip") {
            config.pi_ip = val;
        } else if (key == "pi_port") {
            config.pi_port = std::stoi(val);
        } else if (key == "resolution") {
            config.resolution = val;
        } else if (key == "framerate") {
            config.framerate = std::stoi(val);
        } else if (key == "tmc_dev") {
            config.tmc_dev = val;
        }
    }

    Logger::info(TAG, "Config loaded from " + path + ": Pi IP=" + config.pi_ip + 
                      ", Port=" + std::to_string(config.pi_port) + 
                      ", Res=" + config.resolution + 
                      ", FPS=" + std::to_string(config.framerate) + 
                      ", TMC Dev=" + config.tmc_dev);
    return true;
}
