#ifndef _LENS_CONTROLLER_HPP_
#define _LENS_CONTROLLER_HPP_

#include "TmcDriver.hpp"
#include <memory>

class LensController {
private:
    std::shared_ptr<TmcDriver> m_driver;
    int m_zoom_pos = 0;
    int m_focus_pos = 0;
    int m_zoom_max = 10000;
    int m_focus_max = 10000;

public:
    LensController(std::shared_ptr<TmcDriver> driver);
    ~LensController();

    bool init_limits();
    bool calibrate();
    
    // Zoom motor actions
    bool zoom_to(int position);
    bool zoom_step(int steps); // positive = zoom in, negative = zoom out
    int get_zoom_position();

    // Focus motor actions
    bool focus_to(int position);
    bool focus_step(int steps); // positive = focus near, negative = focus far
    int get_focus_position();

    // P-Iris actions
    bool iris_to(int position);
};

#endif
