import type { ATKHeaders, ErrorCode, ErrorResponse, RequestBody } from '../types';

export function jsonError(error: ErrorCode, message: string, status: number): Response {
  const body: ErrorResponse = { error, message };
  return Response.json(body, { status });
}

export function extractHeaders(req: Request, requireTxId = false): ATKHeaders | Response {
  const agentId = req.headers.get('X-ATK-Agent-Id');
  const nonce = req.headers.get('X-ATK-Nonce');
  const timestamp = req.headers.get('X-ATK-Timestamp');
  const signature = req.headers.get('X-ATK-Signature');
  const transactionId = req.headers.get('X-ATK-Transaction-Id') ?? undefined;

  if (!agentId || !nonce || !timestamp || !signature) {
    return jsonError('MISSING_HEADERS', 'Mandatory validation headers are missing', 401);
  }

  if (requireTxId && !transactionId) {
    return jsonError('MISSING_HEADERS', 'X-ATK-Transaction-Id is required for settlement', 401);
  }

  return { agentId, nonce, timestamp, signature, transactionId };
}

export async function parseBody(req: Request): Promise<RequestBody | Response> {
  try {
    const body = (await req.json()) as RequestBody;
    if (!body.phase || !body.tool_name || body.args === undefined) {
      return jsonError('MISSING_HEADERS', 'Request body is missing required fields', 401);
    }
    return body;
  } catch {
    return jsonError('MISSING_HEADERS', 'Invalid JSON body', 401);
  }
}

export function parsePrepareBody(req: Request): Promise<Record<string, unknown>> {
  return req.json() as Promise<Record<string, unknown>>;
}
