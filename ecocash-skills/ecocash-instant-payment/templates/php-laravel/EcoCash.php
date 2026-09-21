<?php

namespace App\Services;

use Illuminate\Http\Client\PendingRequest;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;

class EcoCash
{
    private function http(): PendingRequest
    {
        return Http::baseUrl(rtrim(config('services.ecocash.base_url'), '/'))
            ->withBasicAuth(config('services.ecocash.username'), config('services.ecocash.password'))
            ->acceptJson()
            ->asJson()
            ->timeout(30);
    }

    /** Fields every charge and refund carries. */
    private function merchant(): array
    {
        $c = config('services.ecocash');

        return [
            'merchantCode'      => $c['merchant_code'],
            'merchantPin'       => $c['merchant_pin'],
            'merchantNumber'    => $c['merchant_number'],
            'countryCode'       => 'ZW',
            'terminalID'        => $c['terminal_id'],
            'location'          => $c['location'],
            'superMerchantName' => $c['super_merchant_name'],
            'merchantName'      => $c['merchant_name'],
        ];
    }

    private function amount(string $amount, string $currency, string $description): array
    {
        return [
            'charginginformation' => [
                'amount'      => number_format((float) $amount, 2, '.', ''), // "2.00" - see section 4.5
                'currency'    => $currency,
                'description' => $description,
            ],
            'chargeMetaData' => ['channel' => config('services.ecocash.channel')],
        ];
    }

    /** Start a charge. Persist $correlator BEFORE calling this. */
    public function charge(string $msisdn, string $amount, string $currency, string $reference,
                           string $correlator, string $notifyUrl = ''): array
    {
        $payload = [
            'clientCorrelator'           => $correlator,
            'notifyUrl'                  => $notifyUrl,
            'referenceCode'              => $reference,
            'tranType'                   => 'MER',
            'endUserId'                  => $msisdn,
            'remarks'                    => $reference,
            'transactionOperationStatus' => 'Charged',
            'paymentAmount'              => $this->amount($amount, $currency, $reference),
        ] + $this->merchant();

        return $this->http()->post('/transactions/amount/', $payload)->throw()->json();
    }

    public function lookup(string $msisdn, string $correlator): array
    {
        return $this->http()
            ->get('/'.rawurlencode($msisdn).'/transactions/amount/'.rawurlencode($correlator))
            ->throw()->json();
    }

    public function refund(string $msisdn, string $originalReference, string $amount,
                           string $currency, string $reference): array
    {
        $payload = [
            'clientCorrelator'         => (string) Str::uuid(), // a NEW correlator
            'referenceCode'            => $reference,
            'tranType'                 => config('services.ecocash.refund_tran_type'),
            'endUserId'                => $msisdn,
            'originalEcocashReference' => $originalReference,
            'remarks'                  => $reference,
            'paymentAmount'            => $this->amount($amount, $currency, 'Refund'),
        ] + $this->merchant();

        return $this->http()->post('/transactions/refund/', $payload)->throw()->json();
    }

    /** The API documents `status`; the portal's SDK samples read two other names. */
    public static function status(array $body): ?string
    {
        return $body['status'] ?? $body['transactionStatus'] ?? $body['transactionOperationStatus'] ?? null;
    }

    /** The reference a refund needs as originalEcocashReference. */
    public static function reference(array $body): ?string
    {
        return $body['ecocashReference'] ?? $body['transactionId'] ?? null;
    }
}
