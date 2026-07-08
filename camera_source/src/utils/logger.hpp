#ifndef _LOGGER_HPP_
#define _LOGGER_HPP_

#include <string>
#include <iostream>
#include <mutex>

enum class LogLevel {
    DEBUG,
    INFO,
    WARN,
    ERROR
};

class Logger {
private:
    static LogLevel m_log_level;
    static std::mutex m_log_mutex;

public:
    static void set_level(LogLevel level);
    static void log(LogLevel level, const std::string& tag, const std::string& message);
    static void info(const std::string& tag, const std::string& message);
    static void error(const std::string& tag, const std::string& message);
    static void warn(const std::string& tag, const std::string& message);
    static void debug(const std::string& tag, const std::string& message);
};

#endif
