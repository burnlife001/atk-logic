#pragma once
#include <QString>

class QBreakpadHandler {
public:
    void setDumpPath(const QString&) {}
    void setDumpPath(const QString&, const QString&) {}
};

static QBreakpadHandler QBreakpadInstance;
