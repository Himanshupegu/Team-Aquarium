export function formatIST(dateString?: string): string {
    if (!dateString) return "";
    try {
        // If it's a "HH:MM:SS" only string (used in AgentLogRow)
        if (/^\d{2}:\d{2}:\d{2}$/.test(dateString.trim())) {
            // Append a dummy date to parse the time
            const d = new Date(`1970-01-01T${dateString.trim()}Z`);
            if (isNaN(d.getTime())) return dateString;
            return d.toLocaleTimeString('en-IN', {
                timeZone: 'Asia/Kolkata',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            });
        }

        // Otherwise assume a full date parsing. Assumes UTC from backend if no TZ info
        const utcDate = dateString.endsWith('Z') || dateString.includes('+')
            ? dateString
            : dateString.replace(' ', 'T') + 'Z';

        const d = new Date(utcDate);
        if (isNaN(d.getTime())) return dateString;

        return d.toLocaleString('en-IN', {
            timeZone: 'Asia/Kolkata',
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
    } catch {
        return dateString;
    }
}
