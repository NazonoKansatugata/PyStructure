import * as cp from 'node:child_process';

import { CliPayload } from './resultsView';

type CliError = Error & {
  stderr?: string;
  command?: string;
};

export async function runPyStructureCli(scriptPath: string, workspacePath: string): Promise<CliPayload> {
  const attempts = [
    { command: 'python', args: [scriptPath, 'analyze', workspacePath, '--json'] },
    { command: 'python3', args: [scriptPath, 'analyze', workspacePath, '--json'] },
    { command: 'py', args: ['-3', scriptPath, 'analyze', workspacePath, '--json'] },
  ];
  const env = {
    ...process.env,
    PYTHONUTF8: '1',
    PYTHONIOENCODING: 'utf-8',
  };

  let lastError: CliError | undefined;

  for (const attempt of attempts) {
    try {
      const stdout = await new Promise<string>((resolve, reject) => {
        cp.execFile(
          attempt.command,
          attempt.args,
          { env, maxBuffer: 64 * 1024 * 1024 },
          (error: Error | null, stdoutText: string, stderrText: string) => {
            if (error) {
              const cliError = error as CliError;
              cliError.stderr = stderrText;
              cliError.command = `${attempt.command} ${attempt.args.join(' ')}`;
              reject(cliError);
              return;
            }

            resolve(stdoutText);
          }
        );
      });

      return JSON.parse(stdout) as CliPayload;
    } catch (error) {
      lastError = error as CliError;
    }
  }

  const error: CliError = lastError ?? new Error('PyStructure CLI の起動に失敗しました。');
  const messageLines = ['PyStructure CLI の起動に失敗しました。'];

  if (error.command) {
    messageLines.push(`Command: ${error.command}`);
  }

  if (error.message) {
    messageLines.push(`Message: ${error.message}`);
  }

  if (error.stderr) {
    messageLines.push('stderr:', error.stderr.trim() || '(empty)');
  }

  throw new Error(messageLines.join('\n'));
}
