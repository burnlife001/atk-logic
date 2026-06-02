#ifndef THREAD_CMD_H
#define THREAD_CMD_H

#include <QObject>
#include <QTcpServer>
#include <QTcpSocket>
#include <QJsonObject>
#include <QJsonDocument>
#include <QJsonArray>
#include <QString>

class SessionController;
class DataService;

class CmdServer : public QObject
{
    Q_OBJECT

    enum State { Idle, Capturing, Saving };

public:
    explicit CmdServer(QObject *parent = nullptr);
    void startServer(quint16 port = 9876);

private slots:
    void onNewConnection();
    void onReadyRead();
    void onDisconnected();
    void onCaptureProgress(qint32 schedule, qint32 type, qint32 state);
    void onSaveProgress(qint32 schedule);

private:
    void handleStart(const QJsonObject &json);
    void handleStop();
    void handleDebug(const QJsonObject &);
    void sendResponse(const QJsonObject &json);

    QTcpServer *m_server;
    QTcpSocket *m_client = nullptr;
    SessionController *m_sessionController = nullptr;
    DataService *m_dataService = nullptr;
    QString m_outputPath;
    State m_state = Idle;
    double m_durationS = 0;
    int m_sampleRateHz = 0;
};

#endif // THREAD_CMD_H
