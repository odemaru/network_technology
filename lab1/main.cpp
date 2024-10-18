#include <algorithm>
#include <arpa/inet.h>
#include <chrono>
#include <iostream>
#include <sys/socket.h>
#include <sys/poll.h>
#include <map>
#include <thread>
#include <unistd.h>

#define BUFFER_SIZE 512
#define WAIT_TIMEOUT 1000
#define TIMEOUT 3113
#define PORT 1337
#define SEND_TIME 1000

void SendMulticast(int sock, sockaddr_in groupAddr) {
    std::string message = std::to_string(ntohs(groupAddr.sin_port));
    if (!sendto(sock, message.c_str(), message.size(), 0, (sockaddr*)&groupAddr, sizeof(groupAddr))) {
        perror("sendto");
    }
}

void MainPrint(std::map<std::string, std::chrono::time_point<std::chrono::steady_clock>> &ALIVE) {
    if (!ALIVE.empty()) std::cout << "CURRENT PROGS: " << std::endl;

    for (const auto& pair : ALIVE) {
        std::cout << pair.first << std::endl;
    }
}

void ReceiveMulticast(int sock, struct pollfd* pdf, std::map<std::string, std::chrono::time_point<std::chrono::steady_clock>>& ALIVE) {
    char buffer[BUFFER_SIZE + 1];
    sockaddr_in senderAddr{};
    socklen_t senderAddrLen = sizeof(senderAddr);

    int events = poll(pdf, 1, WAIT_TIMEOUT);

    if (events == 0) {
        return;
    }

    ssize_t recvLen = recvfrom(sock, buffer, BUFFER_SIZE, 0, (sockaddr*)&senderAddr, &senderAddrLen);

    if (recvLen > 0) {
        buffer[recvLen] = '\0';
        std::string sender = inet_ntoa(senderAddr.sin_addr);
        std::string key = sender + ":" + std::to_string(senderAddr.sin_port);

        if (!ALIVE.count(key)) {
            ALIVE[key] = std::chrono::steady_clock::now();
            MainPrint(ALIVE);
        } else {
            ALIVE[key] = std::chrono::steady_clock::now();
        }

    } else if (recvLen == -1) {
        perror("recfrom");
    }
}

void Cleaner(std::map<std::string, std::chrono::time_point<std::chrono::steady_clock>>& ALIVE) {
    for (auto pair = ALIVE.begin(); pair != ALIVE.end(); ) {
        auto now = std::chrono::steady_clock::now();
        auto timeout = std::chrono::duration_cast<std::chrono::milliseconds>(now - pair->second);
        if (timeout.count() >= TIMEOUT) {
            pair = ALIVE.erase(pair);
            MainPrint(ALIVE);
        } else {
            ++pair;
        }
    }
}

int main(int argc, char* argv[]) {
    if (argc != 2) {
        std::cerr << "usage: " << argv[0] << " <Multicast address>" << std::endl;
        return 1;
    }

    std::string multicastAddr = argv[1];

    int recvSock = socket(AF_INET, SOCK_DGRAM, 0);
    if (recvSock < 0) {
        perror("socket");
        return 1;
    }

    int opt = 1;
    if (setsockopt(recvSock, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
        perror("setsockopt");
        return 1;
    }

    sockaddr_in localAddr{};
    localAddr.sin_family = AF_INET;
    localAddr.sin_port = htons(PORT);
    localAddr.sin_addr.s_addr = htonl(INADDR_ANY);

    if (bind(recvSock, (sockaddr*)&localAddr, sizeof(localAddr)) < 0) {
        perror("bind");
        return 1;
    }

    int sendSock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sendSock < 0) {
        perror("socket");
        return 1;
    }

    sockaddr_in groupAddr{};
    groupAddr.sin_family = AF_INET;
    groupAddr.sin_port = htons(PORT);

    if (inet_pton(AF_INET, multicastAddr.c_str(), &groupAddr.sin_addr) <= 0) {
        std::cerr << "invalid multicast address" << std::endl;
        return 1;
    }

    ip_mreq mreq{};
    mreq.imr_multiaddr = groupAddr.sin_addr;
    mreq.imr_interface.s_addr = htonl(INADDR_ANY);

    if (setsockopt(recvSock, IPPROTO_IP, IP_ADD_MEMBERSHIP, &mreq, sizeof(mreq))) {
        perror("setsockopt");
        return 1;
    }

    struct pollfd pfd[1];
    pfd[0].fd = recvSock;
    pfd[0].events = POLLIN;

    std::map<std::string, std::chrono::time_point<std::chrono::steady_clock>> ALIVE;

    auto notNow = std::chrono::steady_clock::now();

    while (true) {
        ReceiveMulticast(recvSock, pfd, ALIVE);

        auto now = std::chrono::steady_clock::now();
        auto timeout = std::chrono::duration_cast<std::chrono::milliseconds>(now - notNow);

        if (timeout.count() >= SEND_TIME) {
            SendMulticast(sendSock, groupAddr);
            notNow = now;
        }

        Cleaner(ALIVE);
    }

    return 0;
}
