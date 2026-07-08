#ifndef _TMC_DRIVER_HPP_
#define _TMC_DRIVER_HPP_

#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <cstdint>
#include <mutex>
#include <memory>
#include <string>

// Define ioctl macros
#define SET_GAIN_STEP        _IOW('a', 'l', int32_t *)

#define SET_ZOOM_POSITION    _IOW('a', 'a', int32_t *)  
#define GET_ZOOM_POSITION    _IOR('a', 'b', int32_t *)
#define SET_ZOOM_STEP_CUR    _IOW('a', 'o', int32_t *) 
#define GET_ZOOM_STEP_CUR    _IOR('a', 'k', int32_t *)
#define SET_ZOOM_MAX         _IOW('a', 'r', int32_t *)
#define GET_ZOOM_MAX         _IOR('a', 'g', int32_t *)
#define CALIB_ZOOM           _IOR('a', 'u', int32_t *)
#define REVERSE_DIR_ZOOM     _IOW('o', 'z', int32_t *)

#define SET_FOCUS_POSITION   _IOW('a', 'c', int32_t *)
#define GET_FOCUS_POSITION   _IOR('a', 'd', int32_t *)
#define SET_FOCUS_STEP_CUR   _IOW('a', 'p', int32_t *)
#define GET_FOCUS_STEP_CUR   _IOR('a', 'n', int32_t *)
#define SET_FOCUS_MAX        _IOW('a', 's', int32_t *)
#define GET_FOCUS_MAX        _IOR('a', 'h', int32_t *)
#define CALIB_FOCUS          _IOR('a', 'v', int32_t *)
#define REVERSE_DIR_FOCUS    _IOW('o', 'f', int32_t *)

#define SET_PIRIS_POSITION   _IOW('a', 'e', int32_t *)
#define GET_PIRIS_POSITION   _IOR('a', 'f', int32_t *)
#define SET_PIRIS_STEP_CUR   _IOW('a', 'q', int32_t *)
#define GET_PIRIS_STEP_CUR   _IOR('a', 'm', int32_t *)
#define SET_PIRIS_MAX        _IOW('a', 't', int32_t *) 
#define GET_PIRIS_MAX        _IOR('a', 'i', int32_t *)
#define CALIB_PIRIS          _IOR('a', 'w', int32_t *)

enum class TmcChannel {
    UNKNOWN_MOTOR,
    ZOOM_MOTOR,
    FOCUS_MOTOR,
    PIRIS_MOTOR
};

class TmcDriver {
private:
    int m_dev_fd = -1;
    std::shared_ptr<std::mutex> m_tmc_mtx = std::make_shared<std::mutex>(); 

    TmcDriver();
    bool init(const std::string& dev_path);

public:
    static std::shared_ptr<TmcDriver> create(const std::string& dev_path = "/dev/tmc_dev0");
    virtual ~TmcDriver();

    std::shared_ptr<std::mutex> get_mutex() const { return m_tmc_mtx; }

    bool set_lens_conv_coef(int conv_coef);
    bool set_lens_to_zero(TmcChannel ch);
    bool set_lens_calib();
    bool set_lens_goto(TmcChannel ch, int tar_pos);
    bool set_lens_info(TmcChannel ch, int new_pos);
    bool get_lens_info(TmcChannel ch, int& recv_pos);
    bool set_lens_max(TmcChannel ch, int max);
    bool get_lens_max(TmcChannel ch, int &max);    
    bool reverse_lens_dir(TmcChannel ch, int is_rvs);    
};

#endif
