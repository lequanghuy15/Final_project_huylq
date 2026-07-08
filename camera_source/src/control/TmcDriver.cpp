#include "TmcDriver.hpp"
#include "../utils/logger.hpp"
#include <cstring>
#include <errno.h>

#define TAG "TmcDriver"

TmcDriver::TmcDriver() : m_dev_fd(-1) {}

TmcDriver::~TmcDriver() {
    if (m_dev_fd >= 0) {
        close(m_dev_fd);
    }
}

bool TmcDriver::init(const std::string& dev_path) {
    m_dev_fd = open(dev_path.c_str(), O_RDWR);
    if (m_dev_fd < 0) {
        Logger::error(TAG, "Failed to open character device: " + dev_path + " - " + std::string(strerror(errno)));
        return false;
    }
    Logger::info(TAG, "Successfully opened character device: " + dev_path + " (fd=" + std::to_string(m_dev_fd) + ").");
    return true;
}

std::shared_ptr<TmcDriver> TmcDriver::create(const std::string& dev_path) {
    auto ptr = std::shared_ptr<TmcDriver>(new TmcDriver());
    if (!ptr->init(dev_path)) {
        return nullptr;
    }
    return ptr;
}

bool TmcDriver::set_lens_conv_coef(int conv_coef) {
    std::lock_guard<std::mutex> lock(*m_tmc_mtx);
    int ret = ioctl(m_dev_fd, SET_GAIN_STEP, &conv_coef);
    if (ret < 0) {
        Logger::error(TAG, "ioctl SET_GAIN_STEP failed: " + std::string(strerror(errno)));
        return false;
    }
    return true;
}

bool TmcDriver::set_lens_to_zero(TmcChannel ch) {
    unsigned long cmd = 0;
    switch (ch) {
        case TmcChannel::ZOOM_MOTOR:  cmd = CALIB_ZOOM; break;
        case TmcChannel::FOCUS_MOTOR: cmd = CALIB_FOCUS; break;
        case TmcChannel::PIRIS_MOTOR: cmd = CALIB_PIRIS; break;
        default: return false;
    }

    std::lock_guard<std::mutex> lock(*m_tmc_mtx);
    int dummy = 0;
    int ret = ioctl(m_dev_fd, cmd, &dummy);
    if (ret < 0) {
        Logger::error(TAG, "ioctl CALIB failed for channel: " + std::to_string(static_cast<int>(ch)));
        return false;
    }
    return true;
}

bool TmcDriver::set_lens_calib() {
    bool ret = set_lens_to_zero(TmcChannel::ZOOM_MOTOR);
    ret = ret && set_lens_to_zero(TmcChannel::FOCUS_MOTOR);
    return ret;
}

bool TmcDriver::set_lens_goto(TmcChannel ch, int tar_pos) {
    unsigned long cmd = 0;
    switch (ch) {
        case TmcChannel::ZOOM_MOTOR:  cmd = SET_ZOOM_POSITION; break;
        case TmcChannel::FOCUS_MOTOR: cmd = SET_FOCUS_POSITION; break;
        case TmcChannel::PIRIS_MOTOR: cmd = SET_PIRIS_POSITION; break;
        default: return false;
    }

    std::lock_guard<std::mutex> lock(*m_tmc_mtx);
    int val = tar_pos;
    int ret = ioctl(m_dev_fd, cmd, &val);
    if (ret < 0) {
        Logger::error(TAG, "ioctl SET_POSITION failed: " + std::string(strerror(errno)));
        return false;
    }
    return true;
}

bool TmcDriver::set_lens_info(TmcChannel ch, int new_pos) {
    unsigned long cmd = 0;
    switch (ch) {
        case TmcChannel::ZOOM_MOTOR:  cmd = SET_ZOOM_STEP_CUR; break;
        case TmcChannel::FOCUS_MOTOR: cmd = SET_FOCUS_STEP_CUR; break;
        case TmcChannel::PIRIS_MOTOR: cmd = SET_PIRIS_STEP_CUR; break;
        default: return false;
    }

    std::lock_guard<std::mutex> lock(*m_tmc_mtx);
    int val = new_pos;
    int ret = ioctl(m_dev_fd, cmd, &val);
    if (ret < 0) {
        Logger::error(TAG, "ioctl SET_STEP_CUR failed: " + std::string(strerror(errno)));
        return false;
    }
    return true;
}

bool TmcDriver::get_lens_info(TmcChannel ch, int& recv_pos) {
    unsigned long cmd = 0;
    switch (ch) {
        case TmcChannel::ZOOM_MOTOR:  cmd = GET_ZOOM_STEP_CUR; break;
        case TmcChannel::FOCUS_MOTOR: cmd = GET_FOCUS_STEP_CUR; break;
        case TmcChannel::PIRIS_MOTOR: cmd = GET_PIRIS_STEP_CUR; break;
        default: return false;
    }

    std::lock_guard<std::mutex> lock(*m_tmc_mtx);
    int val = 0;
    int ret = ioctl(m_dev_fd, cmd, &val);
    if (ret < 0) {
        Logger::error(TAG, "ioctl GET_STEP_CUR failed: " + std::string(strerror(errno)));
        return false;
    }
    recv_pos = val;
    return true;
}

bool TmcDriver::set_lens_max(TmcChannel ch, int max) {
    unsigned long cmd = 0;
    switch (ch) {
        case TmcChannel::ZOOM_MOTOR:  cmd = SET_ZOOM_MAX; break;
        case TmcChannel::FOCUS_MOTOR: cmd = SET_FOCUS_MAX; break;
        case TmcChannel::PIRIS_MOTOR: cmd = SET_PIRIS_MAX; break;
        default: return false;
    }

    std::lock_guard<std::mutex> lock(*m_tmc_mtx);
    int val = max;
    int ret = ioctl(m_dev_fd, cmd, &val);
    if (ret < 0) {
        Logger::error(TAG, "ioctl SET_MAX failed: " + std::string(strerror(errno)));
        return false;
    }
    return true;
}

bool TmcDriver::get_lens_max(TmcChannel ch, int &max) {
    unsigned long cmd = 0;
    switch (ch) {
        case TmcChannel::ZOOM_MOTOR:  cmd = GET_ZOOM_MAX; break;
        case TmcChannel::FOCUS_MOTOR: cmd = GET_FOCUS_MAX; break;
        case TmcChannel::PIRIS_MOTOR: cmd = GET_PIRIS_MAX; break;
        default: return false;
    }

    std::lock_guard<std::mutex> lock(*m_tmc_mtx);
    int val = 0;
    int ret = ioctl(m_dev_fd, cmd, &val);
    if (ret < 0) {
        Logger::error(TAG, "ioctl GET_MAX failed: " + std::string(strerror(errno)));
        return false;
    }
    max = val;
    return true;
}

bool TmcDriver::reverse_lens_dir(TmcChannel ch, int is_rvs) {
    unsigned long cmd = 0;
    switch (ch) {
        case TmcChannel::ZOOM_MOTOR:  cmd = REVERSE_DIR_ZOOM; break;
        case TmcChannel::FOCUS_MOTOR: cmd = REVERSE_DIR_FOCUS; break;
        default: return false;
    }

    std::lock_guard<std::mutex> lock(*m_tmc_mtx);
    int val = is_rvs;
    int ret = ioctl(m_dev_fd, cmd, &val);
    if (ret < 0) {
        Logger::error(TAG, "ioctl REVERSE_DIR failed: " + std::string(strerror(errno)));
        return false;
    }
    return true;
}
