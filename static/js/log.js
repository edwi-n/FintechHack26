/**
 * Trading Arena — Battle Log Utility
 * Append entries to the on-screen battle log.
 */

function addLog(msg, cls) {
          cls = cls || 'info';
          var entries = document.getElementById('logEntries');
          var div = document.createElement('div');
          div.className = 'log-entry ' + cls;
          div.textContent = msg;
          entries.insertBefore(div, entries.firstChild);
          while (entries.children.length > 50) entries.removeChild(entries.lastChild);
}
