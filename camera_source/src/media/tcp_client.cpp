#include "tcp_client.hpp"
#include "../utils/logger.hpp"
#include <cstring>
#include <errno.h>

#define TAG "TcpClient"

TcpClient::TcpClient(const std::string& ip, int port) 
    : m_server_ip(ip), m_port(port), m_sock_fd(-1), m_connected(false) {
    connect_to_server();
}

TcpClient::~TcpClient() {
    disconnect();
}

bool TcpClient::connect_to_server() {
    std::lock_guard<std::mutex> lock(m_socket_mutex);
    if (m_connected) return true;

    if (m_sock_fd >= 0) {
        close(m_sock_fd);
    }

    m_sock_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (m_sock_fd < 0) {
        Logger::error(TAG, "Failed to create socket: " + std::string(strerror(errno)));
        return false;
    }

    // Set socket timeout to prevent long blocking
    struct timeval timeout;
    timeout.tv_sec = 2;
    timeout.tv_usec = 0;
    setsockopt(m_sock_fd, SOL_SOCKET, SO_SNDTIMEO, (const char*)&timeout, sizeof(timeout));
    setsockopt(m_sock_fd, SOL_SOCKET, SO_RCVTIMEO, (const char*)&timeout, sizeof(timeout));

    sockaddr_in serv_addr{};
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(m_port);
    if (inet_pton(AF_INET, m_server_ip.c_str(), &serv_addr.sin_addr) <= 0) {
        Logger::error(TAG, "Invalid server IP address: " + m_server_ip);
        close(m_sock_fd);
        m_sock_fd = -1;
        return false;
    }

    Logger::info(TAG, "Connecting to Pi YOLO server at " + m_server_ip + ":" + std::to_string(m_port) + "...");
    if (connect(m_sock_fd, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) < 0) {
        Logger::warn(TAG, "Connection failed: " + std::string(strerror(errno)));
        close(m_sock_fd);
        m_sock_fd = -1;
        return false;
    }

    m_connected = true;
    Logger::info(TAG, "Successfully connected to Pi YOLO server.");
    return true;
}

bool TcpClient::send_frame(const cv::Mat& frame) {
    if (frame.empty()) {
        Logger::warn(TAG, "Empty frame received, skipping send.");
        return false;
    }

    if (!m_connected) {
        if (!connect_to_server()) {
            return false;
        }
    }

    // 1. Resize image to 640x640 (as required by YOLO)
    cv::Mat resized_frame;
    cv::resize(frame, resized_frame, cv::Size(640, 640));

    // Ensure contiguous memory layout (24-bit BGR/RGB)
    if (!resized_frame.isContinuous()) {
        resized_frame = resized_frame.clone();
    }

    uint32_t payload_size = resized_frame.total() * resized_frame.elemSize(); // 640 * 640 * 3 = 1,228,800
    
    // 2. Build 4-byte Big-Endian Header containing the payload size
    uint8_t header[4];
    header[0] = (payload_size >> 24) & 0xFF;
    header[1] = (payload_size >> 16) & 0xFF;
    header[2] = (payload_size >> 8) & 0xFF;
    header[3] = payload_size & 0xFF;

    // 3. Send Header followed by Payload
    std::lock_guard<std::mutex> lock(m_socket_mutex);
    
    // Send 4-byte header
    ssize_t sent = send(m_sock_fd, header, sizeof(header), 0);
    if (sent < 0) {
        Logger::error(TAG, "Failed to send header: " + std::string(strerror(errno)));
        disconnect();
        return false;
    }

    // Send raw frame bytes
    ssize_t total_sent = 0;
    const uint8_t* data_ptr = resized_frame.data;
    while (total_sent < payload_size) {
        sent = send(m_sock_fd, data_ptr + total_sent, payload_size - total_sent, 0);
        if (sent < 0) {
            Logger::error(TAG, "Failed to send image data: " + std::string(strerror(errno)));
            disconnect();
            return false;
        }
        total_sent += sent;
    }

    return true;
}

void TcpClient::disconnect() {
    std::lock_guard<std::mutex> lock(m_socket_mutex);
    if (m_sock_fd >= 0) {
        close(m_sock_fd);
        m_sock_fd = -1;
    }
    m_connected = false;
    Logger::info(TAG, "Socket disconnected.");
}

bool TcpClient::is_connected() {
    std::lock_guard<std::mutex> lock(m_socket_mutex);
    return m_connected;
}
