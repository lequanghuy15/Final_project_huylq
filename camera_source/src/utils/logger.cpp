#include "logger.hpp"
#include <chrono>
#include <iomanip>
#include <sstream>

LogLevel Logger::m_log_level = LogLevel::INFO;
std::mutex Logger::m_log_mutex;

void Logger::set_level(LogLevel level) {
    std::lock_guard<std::mutex> lock(m_log_mutex);
    m_log_level = level;
}

void Logger::log(LogLevel level, const std::string& tag, const std::string& message) {
    std::lock_guard<std::mutex> lock(m_log_mutex);
    if (level < m_log_level) return;

    auto now = std::chrono::system_clock::now();
    auto in_time_t = std::chrono::system_clock::to_time_t(now);

    std::stringstream ss;
    ss << std::put_time(std::localtime(&in_time_t), "%Y-%m-%d %H:%M:%S");

    std::string level_str;
    switch (level) {
        case LogLevel::DEBUG: level_str = "DEBUG"; break;
        case LogLevel::INFO:  level_str = "INFO";  break;
        case LogLevel::WARN:  level_str = "WARN";  break;
        case LogLevel::ERROR: level_str = "ERROR"; break;
    }

    std::ostream& out = (level == LogLevel::ERROR) ? std::cerr : std::cout;
    out << "[" << ss.str() << "] [" << level_str << "] [" << tag << "] " << message << std::endl;
}

void Logger::info(const std::string& tag, const std::string& message) {
    log(LogLevel::INFO, tag, message);
}

void Logger::error(const std::string& tag, const std::string& message) {
    log(LogLevel::ERROR, tag, message);
}

void Logger::warn(const std::string& tag, const std::string& message) {
    log(LogLevel::WARN, tag, message);
}

void Logger::debug(const std::string& tag, const std::string& message) {
    log(LogLevel::DEBUG, tag, message);
}
