#include "lens_controller.hpp"
#include "../utils/logger.hpp"

#define TAG "LensController"

LensController::LensController(std::shared_ptr<TmcDriver> driver) : m_driver(driver) {
    if (m_driver) {
        init_limits();
    }
}

LensController::~LensController() {}

bool LensController::init_limits() {
    if (!m_driver) return false;

    // Load current motor positions from driver
    int z_pos = 0, f_pos = 0;
    if (m_driver->get_lens_info(TmcChannel::ZOOM_MOTOR, z_pos)) {
        m_zoom_pos = z_pos;
    }
    if (m_driver->get_lens_info(TmcChannel::FOCUS_MOTOR, f_pos)) {
        m_focus_pos = f_pos;
    }

    // Set some sensible default limits (e.g. 10000 steps max)
    m_driver->set_lens_max(TmcChannel::ZOOM_MOTOR, m_zoom_max);
    m_driver->set_lens_max(TmcChannel::FOCUS_MOTOR, m_focus_max);

    Logger::info(TAG, "Limits initialized. Zoom pos: " + std::to_string(m_zoom_pos) + 
                      ", Focus pos: " + std::to_string(m_focus_pos));
    return true;
}

bool LensController::calibrate() {
    if (!m_driver) return false;
    Logger::info(TAG, "Starting lens calibration...");
    bool success = m_driver->set_lens_calib();
    if (success) {
        m_zoom_pos = 0;
        m_focus_pos = 0;
        Logger::info(TAG, "Calibration completed successfully.");
    } else {
        Logger::error(TAG, "Calibration failed.");
    }
    return success;
}

bool LensController::zoom_to(int position) {
    if (!m_driver) return false;
    
    // Bounds check
    if (position < 0) position = 0;
    if (position > m_zoom_max) position = m_zoom_max;

    Logger::info(TAG, "Zooming to position: " + std::to_string(position));
    if (m_driver->set_lens_goto(TmcChannel::ZOOM_MOTOR, position)) {
        m_zoom_pos = position;
        return true;
    }
    return false;
}

bool LensController::zoom_step(int steps) {
    int target = m_zoom_pos + steps;
    return zoom_to(target);
}

int LensController::get_zoom_position() {
    int val = 0;
    if (m_driver && m_driver->get_lens_info(TmcChannel::ZOOM_MOTOR, val)) {
        m_zoom_pos = val;
    }
    return m_zoom_pos;
}

bool LensController::focus_to(int position) {
    if (!m_driver) return false;

    // Bounds check
    if (position < 0) position = 0;
    if (position > m_focus_max) position = m_focus_max;

    Logger::info(TAG, "Focusing to position: " + std::to_string(position));
    if (m_driver->set_lens_goto(TmcChannel::FOCUS_MOTOR, position)) {
        m_focus_pos = position;
        return true;
    }
    return false;
}

bool LensController::focus_step(int steps) {
    int target = m_focus_pos + steps;
    return focus_to(target);
}

int LensController::get_focus_position() {
    int val = 0;
    if (m_driver && m_driver->get_lens_info(TmcChannel::FOCUS_MOTOR, val)) {
        m_focus_pos = val;
    }
    return m_focus_pos;
}

bool LensController::iris_to(int position) {
    if (!m_driver) return false;
    Logger::info(TAG, "Setting P-Iris to: " + std::to_string(position));
    return m_driver->set_lens_goto(TmcChannel::PIRIS_MOTOR, position);
}
