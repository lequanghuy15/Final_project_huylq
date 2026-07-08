#ifndef _CONFIG_LOADER_HPP_
#define _CONFIG_LOADER_HPP_

#include <string>

struct CameraConfig {
    std::string pi_ip = "192.168.8.42";
    int pi_port = 8089;
    std::string resolution = "1920x1080";
    int framerate = 30;
    std::string tmc_dev = "/dev/tmc_dev0";
};

class ConfigLoader {
public:
    static bool load(const std::string& path, CameraConfig& config);
};

#endif
