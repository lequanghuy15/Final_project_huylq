#ifndef _STREAM_HPP_
#define _STREAM_HPP_

#include <string>
#include <vector>
#include <mutex>
#include <gst/gst.h>
#include <gst/app/gstappsink.h>
#include <opencv2/opencv.hpp>

class Stream {
private:
    GstElement* m_pipeline = nullptr;
    GstElement* m_appsink = nullptr;
    std::string m_pipeline_str;
    bool m_is_running = false;
    std::mutex m_stream_mutex;

public:
    Stream(const std::string& resolution = "1920x1080", int framerate = 30);
    ~Stream();

    bool start();
    bool get_frame(cv::Mat& frame);
    void stop();
    bool is_running();
};

#endif
