import React, { useState, useRef } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE || '';

function Config() {
  const [uploadStatus, setUploadStatus] = useState(null);
  const [saInfo, setSaInfo] = useState(null);
  const [filesStatus, setFilesStatus] = useState(null);
  const [files, setFiles] = useState([]);
  const [verifyStatus, setVerifyStatus] = useState(null);
  const [resultData, setResultData] = useState(null);
  const [isDragover, setIsDragover] = useState(false);
  const [isUploaded, setIsUploaded] = useState(false);
  const fileInputRef = useRef(null);

  const escapeHtml = (text) => {
    if (text === null || text === undefined) return '';
    return String(text);
  };

  const handleFile = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    setUploadStatus({ type: 'info', message: 'Uploading...', loading: true });

    try {
      const response = await fetch(`${API_BASE}/api/upload-sa`, {
        method: 'POST',
        body: formData
      });
      const data = await response.json();

      if (data.success) {
        setUploadStatus({ type: 'success', message: '✅ Service account uploaded successfully!' });
        setSaInfo({
          projectId: data.project_id,
          clientEmail: data.client_email
        });
        setIsUploaded(true);
      } else {
        setUploadStatus({ type: 'error', message: `❌ ${escapeHtml(data.error)}` });
      }
    } catch (error) {
      setUploadStatus({ type: 'error', message: `❌ Connection error: ${escapeHtml(error.message)}` });
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragover(false);
    if (e.dataTransfer.files.length) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragover(true);
  };

  const handleDragLeave = () => {
    setIsDragover(false);
  };

  const handleFileInputChange = (e) => {
    if (e.target.files.length) {
      handleFile(e.target.files[0]);
    }
  };

  const handleListFiles = async () => {
    setFilesStatus({ type: 'info', message: 'Loading files...', loading: true });
    setFiles([]);

    try {
      const response = await fetch(`${API_BASE}/api/files`);
      const data = await response.json();

      if (data.error) {
        setFilesStatus({ type: 'error', message: `❌ ${escapeHtml(data.error)}` });
      } else {
        setFilesStatus({ type: 'success', message: `✅ Found ${data.count} file(s)` });
        setFiles(data.files || []);
      }
    } catch (error) {
      setFilesStatus({ type: 'error', message: `❌ Connection error: ${escapeHtml(error.message)}` });
    }
  };

  const pollStatus = async (jobId) => {
    try {
      const response = await fetch(`${API_BASE}/api/verify-status/${jobId}`);
      const data = await response.json();

      if (data.status === 'running' || data.status === 'pending') {
        setVerifyStatus({ type: 'pending', message: escapeHtml(data.step) || 'Processing...', loading: true });
        setTimeout(() => pollStatus(jobId), 1000);
      } else if (data.status === 'completed') {
        setVerifyStatus({ type: 'success', message: `✅ ${escapeHtml(data.result.message)}` });
        setResultData(data.result);
      } else if (data.status === 'error') {
        setVerifyStatus({ type: 'error', message: `❌ ${escapeHtml(data.error)}` });
      }
    } catch (error) {
      setVerifyStatus({ type: 'error', message: `❌ Connection error: ${escapeHtml(error.message)}` });
    }
  };

  const handleStartVerify = async () => {
    setVerifyStatus({ type: 'info', message: 'Starting verification...', loading: true });
    setResultData(null);

    try {
      const response = await fetch(`${API_BASE}/api/start-verify`, {
        method: 'POST'
      });
      const data = await response.json();

      if (data.error) {
        setVerifyStatus({ type: 'error', message: `❌ ${escapeHtml(data.error)}` });
      } else {
        pollStatus(data.job_id);
      }
    } catch (error) {
      setVerifyStatus({ type: 'error', message: `❌ Connection error: ${escapeHtml(error.message)}` });
    }
  };

  return (
    <div className="container">
      <h1 className="page-title">🔐 Google Sheets Access Verification</h1>

      {/* Step 1: Upload Service Account */}
      <div className="card">
        <h2 className="card-title">
          <span className="step">1</span> Upload Service Account JSON
        </h2>
        <div
          className={`upload-area ${isDragover ? 'dragover' : ''}`}
          onClick={() => fileInputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
        >
          <div className="upload-icon">📄</div>
          <p>Drag and drop your Service Account JSON file here</p>
          <p>or click to browse</p>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileInputChange}
            accept=".json"
          />
        </div>
        {uploadStatus && (
          <div className={`status ${uploadStatus.type}`}>
            {uploadStatus.loading && <span className="loader"></span>}
            {uploadStatus.message}
          </div>
        )}
        {saInfo && (
          <div className="sa-info">
            <div>
              <span className="label">Project ID:</span>
              <div className="value">{saInfo.projectId}</div>
            </div>
            <div>
              <span className="label">Client Email:</span>
              <div className="value">{saInfo.clientEmail}</div>
            </div>
          </div>
        )}
      </div>

      {/* Step 2: List Files */}
      <div className="card">
        <h2 className="card-title">
          <span className="step">2</span> List Accessible Files
        </h2>
        <p className="description">View all Google Sheets accessible by the service account.</p>
        <button className="btn" onClick={handleListFiles} disabled={!isUploaded}>
          List Files
        </button>
        {filesStatus && (
          <div className={`status ${filesStatus.type}`}>
            {filesStatus.loading && <span className="loader"></span>}
            {filesStatus.message}
          </div>
        )}
        {files.length > 0 && (
          <div className="files-list">
            {files.map((file, index) => (
              <div key={index} className="file-item">
                <div className="file-icon">📊</div>
                <div className="file-name">{file.name}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Step 3: Verify Access */}
      <div className="card">
        <h2 className="card-title">
          <span className="step">3</span> Verify Access & Export
        </h2>
        <p className="description">
          Start a verification job that exports the first Google Sheet to XLSX and parses it with pandas.
        </p>
        <button className="btn" onClick={handleStartVerify} disabled={!isUploaded}>
          Start Verification
        </button>
        {verifyStatus && (
          <div className={`status ${verifyStatus.type}`}>
            {verifyStatus.loading && <span className="loader"></span>}
            {verifyStatus.message}
          </div>
        )}
        {resultData && resultData.sample_data && resultData.sample_data.length > 0 && (
          <div className="result-data">
            <p><strong>Exported File:</strong> {resultData.exported_file}</p>
            <p><strong>Total Rows:</strong> {resultData.row_count}</p>
            <p><strong>Sample Data (first 5 rows):</strong></p>
            <table>
              <thead>
                <tr>
                  {resultData.columns.map((col, index) => (
                    <th key={index}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {resultData.sample_data.map((row, rowIndex) => (
                  <tr key={rowIndex}>
                    {resultData.columns.map((col, colIndex) => (
                      <td key={colIndex}>{row[col]}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default Config;
