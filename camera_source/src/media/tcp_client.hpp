#ifndef _TCP_CLIENT_HPP_
#define _TCP_CLIENT_HPP_

#include <string>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>
#include <opencv2/opencv.hpp>
#include <mutex>

class TcpClient {
private:
    int m_sock_fd = -1;
    std::string m_server_ip;
    int m_port;
    bool m_connected = false;
    std::mutex m_socket_mutex;

    bool connect_to_server();

public:
    TcpClient(const std::string& ip, int port);
    ~TcpClient();

    bool send_frame(const cv::Mat& frame);
    void disconnect();
    bool is_connected();
};

#endif
