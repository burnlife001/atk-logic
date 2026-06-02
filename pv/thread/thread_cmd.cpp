#include "thread_cmd.h"
#include "pv/controller/session_controller.h"
#include "pv/controller/setting.h"
#include "pv/static/data_service.h"
#include "pv/static/log_help.h"
#include <QFile>

CmdServer::CmdServer(QObject *parent)
    : QObject(parent)
    , m_dataService(DataService::getInstance())
{
    m_server = new QTcpServer(this);
    connect(m_server, &QTcpServer::newConnection, this, &CmdServer::onNewConnection);
}

void CmdServer::startServer(quint16 port)
{
    if (m_server->listen(QHostAddress::LocalHost, port)) {
        LogHelp::write(QString("[CLI] TCP server on 127.0.0.1:%1").arg(port));
    } else {
        LogHelp::write(QString("[CLI] TCP server failed: %1").arg(m_server->errorString()));
    }
}

void CmdServer::onNewConnection()
{
    if (m_client) {
        QTcpSocket *rejected = m_server->nextPendingConnection();
        rejected->disconnectFromHost();
        rejected->deleteLater();
        return;
    }
    m_client = m_server->nextPendingConnection();
    connect(m_client, &QTcpSocket::readyRead, this, &CmdServer::onReadyRead);
    connect(m_client, &QTcpSocket::disconnected, this, &CmdServer::onDisconnected);
    LogHelp::write("[CLI] Client connected");
}

void CmdServer::onDisconnected()
{
    LogHelp::write("[CLI] Client disconnected");
    if (m_client) {
        m_client->deleteLater();
        m_client = nullptr;
    }
}

void CmdServer::onReadyRead()
{
    if (!m_client)
        return;

    QByteArray data = m_client->readAll();
    QJsonParseError parseError;
    QJsonDocument doc = QJsonDocument::fromJson(data, &parseError);
    if (!doc.isObject()) {
        sendResponse({{"status", "error"}, {"msg", QString("invalid JSON: %1").arg(parseError.errorString())}});
        return;
    }

    QJsonObject json = doc.object();
    QString cmd = json["cmd"].toString();

    if (cmd == "start") {
        handleStart(json);
    } else if (cmd == "stop") {
        handleStop();
    } else if (cmd == "debug") {
        handleDebug(json);
    } else {
        sendResponse({{"status", "error"}, {"msg", QString("unknown command: %1").arg(cmd)}});
    }
}

void CmdServer::handleStart(const QJsonObject &json)
{
    if (m_state != Idle) {
        sendResponse({{"status", "error"}, {"msg", "capture already in progress"}});
        return;
    }

    m_durationS = json["duration_s"].toDouble(5.0);
    m_outputPath = json["output"].toString("data/capture.atkdl");

    // Use QML's own SessionController and settings — same path as GUI button click.
    // Read settingData/channelsSet from the QML SSettings object so the FPGA
    // receives the exact same configuration as a GUI-initiated capture.
    QObject *root = m_dataService->getRoot();
    if (!root) {
        sendResponse({{"status", "error"}, {"msg", "QML not initialized"}});
        return;
    }

    // Use the QML's existing device session (sessionType==1), never create a second one.
    // findChild returns first match (often Demo session), so iterate findChildren.
    QList<SessionController *> controllers = root->findChildren<SessionController *>();
    SessionController *deviceSC = nullptr;
    for (auto *sc : controllers) {
        if (sc->sessionType() == 1) {
            deviceSC = sc;
            break;
        }
    }
    if (!deviceSC) {
        sendResponse({{"status", "error"}, {"msg", "device not connected in GUI — connect first"}});
        return;
    }
    m_sessionController = deviceSC;

    // Read QML settings from SSettings (same object SideBar.start() reads from)
    QObject *sessionQml = m_sessionController->parent();
    if (!sessionQml) {
        sendResponse({{"status", "error"}, {"msg", "QML session not found"}});
        return;
    }

    QJsonObject settingData;
    QJsonArray channelsSet;
    bool isInstantly = true;

    Setting *sSettings = sessionQml->findChild<Setting *>();
    if (sSettings) {
        QVariant sd = sSettings->property("settingData");
        if (sd.canConvert<QJsonObject>())
            settingData = sd.toJsonObject();
        else if (sd.canConvert<QVariantMap>())
            settingData = QJsonObject::fromVariantMap(sd.toMap());

        QVariant cs = sSettings->property("channelsSet");
        if (cs.canConvert<QJsonArray>())
            channelsSet = cs.toJsonArray();
        else if (cs.canConvert<QVariantList>()) {
            QVariantList list = cs.toList();
            channelsSet = QJsonArray::fromVariantList(list);
        }

        isInstantly = sSettings->property("isInstantly").toBool();
        LogHelp::write("[CLI] Using QML SSettings for capture parameters");
    } else {
        sendResponse({{"status", "error"}, {"msg", "QML settings not found"}});
        return;
    }

    // Apply CLI overrides: duration and output path
    settingData["setTime"] = m_durationS * 1000.0;
    m_sampleRateHz = (int)settingData["setHz"].toDouble();

    // Wire up signals
    connect(m_sessionController, &SessionController::saveSessionSettings,
            this, [](const QString &path) {
                QFile f(path + "/set.ini");
                f.open(QIODevice::WriteOnly | QIODevice::Truncate);
                f.close();
            }, Qt::UniqueConnection);
    connect(m_sessionController, &SessionController::sendDeviceRecvSchedule,
            this, &CmdServer::onCaptureProgress, Qt::UniqueConnection);
    connect(m_sessionController, &SessionController::sendZipDirSchedule,
            this, &CmdServer::onSaveProgress, Qt::UniqueConnection);

    m_sessionController->setFilePath(m_outputPath);

    // Build start JSON exactly as SideBar.start() would
    QJsonObject startJson;
    startJson["settingData"] = settingData;
    startJson["isInstantly"] = isInstantly;
    startJson["channelsSet"] = channelsSet;

    m_state = Capturing;
    bool ok = m_sessionController->start(startJson, 0);
    if (!ok) {
        m_state = Idle;
        sendResponse({{"status", "error"}, {"msg", "failed to start capture (USB communication error)"}});
        return;
    }

    LogHelp::write(QString("[CLI] Capture started: rate=%1Hz dur=%2s output=%3")
                       .arg(m_sampleRateHz)
                       .arg(m_durationS)
                       .arg(m_outputPath));
}

void CmdServer::handleStop()
{
    if (m_state != Capturing) {
        sendResponse({{"status", "error"}, {"msg", "no capture in progress"}});
        return;
    }

    m_sessionController->stop();
    m_state = Idle;
    sendResponse({{"status", "ok"}});
    LogHelp::write("[CLI] Capture stopped by client");
}

void CmdServer::onCaptureProgress(qint32 schedule, qint32 type, qint32 state)
{
    // type 0 = start, 1/2 = buffer progress, 3 = pre-trigger, 7 = post-trigger
    // type 4 = save file progress
    // type 6 = load file progress (not used here)
    if (m_state == Capturing && type != 4) {
        if (schedule >= 100) {
            if (state == 1 && m_sessionController) {
                // Capture done, start saving
                m_state = Saving;
                m_sessionController->saveData(m_outputPath, "CLI_Capture");
                LogHelp::write("[CLI] Capture complete, saving file...");
            } else {
                m_state = Idle;
                sendResponse({{"status", "error"}, {"msg", "capture stopped or failed"}});
            }
        } else {
            sendResponse({
                {"status", "progress"},
                {"phase", "capture"},
                {"schedule", schedule}
            });
        }
    } else if (m_state == Saving && type == 4 && schedule >= 100) {
        m_state = Idle;
        sendResponse({
            {"status", "ok"},
            {"file", m_outputPath},
            {"sample_rate_hz", m_sampleRateHz},
            {"duration_s", m_durationS}
        });
        LogHelp::write(QString("[CLI] File saved: %1").arg(m_outputPath));
    }
}

void CmdServer::onSaveProgress(qint32 schedule)
{
    if (m_state == Saving) {
        sendResponse({
            {"status", "progress"},
            {"phase", "save"},
            {"schedule", schedule}
        });
    }
}

void CmdServer::handleDebug(const QJsonObject &)
{
    QJsonObject info;
    QObject *root = m_dataService->getRoot();
    if (!root) {
        sendResponse({{"status", "error"}, {"msg", "no root"}});
        return;
    }

    // List all SessionController children
    QList<SessionController *> allSC = root->findChildren<SessionController *>();
    QJsonArray scList;
    for (auto *sc : allSC) {
        QJsonObject scInfo;
        scInfo["sessionName"] = sc->sessionName();
        scInfo["sessionType"] = sc->sessionType();
        scInfo["sessionPort"] = sc->sessionPort();
        scInfo["isInit"] = sc->isInit();
        QObject *parent = sc->parent();
        scInfo["parentType"] = parent ? parent->metaObject()->className() : "null";
        // Check parent's parent
        QObject *pp = parent ? parent->parent() : nullptr;
        scInfo["parentParentType"] = pp ? pp->metaObject()->className() : "null";
        scList.append(scInfo);
    }

    info["status"] = "ok";
    info["rootType"] = root->metaObject()->className();
    info["sessionControllerCount"] = allSC.size();
    info["sessionControllers"] = scList;

    sendResponse(info);
}

void CmdServer::sendResponse(const QJsonObject &json)
{
    if (!m_client || m_client->state() != QAbstractSocket::ConnectedState)
        return;

    QByteArray data = QJsonDocument(json).toJson(QJsonDocument::Compact);
    data.append('\n');
    m_client->write(data);
}
