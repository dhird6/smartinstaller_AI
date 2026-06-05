# TestApp Installation Failures — Download & Network

## Symptoms
- Partial download detected
- Checksum mismatch or invalid checksum
- CDN unavailable (HTTP 503)
- Connection reset during download

## Root Causes
- Unstable network connection
- Proxy or firewall blocking CDN endpoints
- Corrupted download cache
- Authentication token expired

## Diagnosis
- Verify internet connectivity and DNS resolution
- Check proxy settings: `netsh winhttp show proxy`
- Compare downloaded file size against expected package size
- Review installer log for HTTP error codes (401, 503)

## Resolution
1. Retry download on a stable network connection
2. Disable VPN temporarily or configure proxy exceptions
3. Clear browser/download cache and re-download
4. Verify authentication credentials or download token validity
5. Use offline installer package if available
