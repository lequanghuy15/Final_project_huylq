#include "stream.hpp"
#include "../utils/logger.hpp"
#include <sstream>

#define TAG "Stream"

Stream::Stream(const std::string& resolution, int framerate) {
    // 1. Initialize GStreamer once
    static bool gstreamer_initialized = false;
    if (!gstreamer_initialized) {
        gst_init(NULL, NULL);
        gstreamer_initialized = true;
        Logger::info(TAG, "GStreamer initialized successfully.");
    }

    // 2. Parse resolution (e.g., "1920x1080")
    std::string width = "1920";
    std::string height = "1080";
    size_t x_pos = resolution.find('x');
    if (x_pos != std::string::npos) {
        width = resolution.substr(0, x_pos);
        height = resolution.substr(x_pos + 1);
    }

    // 3. Construct GStreamer pipeline string
    // We use olcamerasrc src_2 pad which outputs JPEG, then pull it via appsink named jpeg_sink.
    std::stringstream ss;
    ss << "olcamerasrc name=ol ol.src_2 ! image/jpeg, width=" << width 
       << ", height=" << height << ", framerate=" << framerate 
       << "/1 ! queue leaky=downstream max-size-buffers=1 ! appsink name=jpeg_sink max-buffers=1 drop=true";
    
    m_pipeline_str = ss.str();
    Logger::info(TAG, "GStreamer Pipeline String: " + m_pipeline_str);
}

Stream::~Stream() {
    stop();
}

bool Stream::start() {
    std::lock_guard<std::mutex> lock(m_stream_mutex);
    if (m_is_running) return true;

    GError* error = nullptr;
    m_pipeline = gst_parse_launch(m_pipeline_str.c_str(), &error);
    if (error != nullptr) {
        Logger::error(TAG, "Failed to launch pipeline: " + std::string(error->message));
        g_error_free(error);
        return false;
    }

    m_appsink = gst_bin_get_by_name(GST_BIN(m_pipeline), "jpeg_sink");
    if (!m_appsink) {
        Logger::error(TAG, "Failed to get appsink element named 'jpeg_sink'.");
        gst_object_unref(m_pipeline);
        m_pipeline = nullptr;
        return false;
    }

    // Set appsink settings to prevent frame accumulation and latency
    g_object_set(m_appsink, "emit-signals", FALSE, "sync", FALSE, NULL);

    Logger::info(TAG, "Setting GStreamer pipeline to PLAYING...");
    GstStateChangeReturn ret = gst_element_set_state(m_pipeline, GST_STATE_PLAYING);
    if (ret == GST_STATE_CHANGE_FAILURE) {
        Logger::error(TAG, "Failed to set pipeline to PLAYING state.");
        gst_object_unref(m_appsink);
        gst_object_unref(m_pipeline);
        m_appsink = nullptr;
        m_pipeline = nullptr;
        return false;
    }

    m_is_running = true;
    Logger::info(TAG, "GStreamer pipeline is running.");
    return true;
}

bool Stream::get_frame(cv::Mat& frame) {
    if (!m_is_running || !m_appsink) {
        return false;
    }

    // Pull sample from appsink (with a 2-second timeout)
    GstSample* sample = gst_app_sink_try_pull_sample(GST_APP_SINK(m_appsink), 2000000000ULL);
    if (!sample) {
        Logger::warn(TAG, "Failed to pull sample from GStreamer appsink (timeout).");
        return false;
    }

    GstBuffer* buffer = gst_sample_get_buffer(sample);
    if (!buffer) {
        gst_sample_unref(sample);
        return false;
    }

    GstMapInfo map;
    if (gst_buffer_map(buffer, &map, GST_MAP_READ)) {
        // Decode the JPEG memory buffer using OpenCV
        std::vector<uint8_t> jpeg_data(map.data, map.data + map.size);
        gst_buffer_unmap(buffer, &map);
        gst_sample_unref(sample);

        if (!jpeg_data.empty()) {
            frame = cv::imdecode(jpeg_data, cv::IMREAD_COLOR); // Decodes to standard BGR format
            return !frame.empty();
        }
    } else {
        gst_sample_unref(sample);
    }

    return false;
}

void Stream::stop() {
    std::lock_guard<std::mutex> lock(m_stream_mutex);
    if (!m_is_running) return;

    Logger::info(TAG, "Stopping GStreamer pipeline...");
    if (m_pipeline) {
        gst_element_set_state(m_pipeline, GST_STATE_NULL);
        gst_object_unref(m_pipeline);
        m_pipeline = nullptr;
    }

    if (m_appsink) {
        m_appsink = nullptr; // refs managed by gst_object_unref(m_pipeline)
    }

    m_is_running = false;
    Logger::info(TAG, "GStreamer pipeline stopped.");
}

bool Stream::is_running() {
    std::lock_guard<std::mutex> lock(m_stream_mutex);
    return m_is_running;
}
