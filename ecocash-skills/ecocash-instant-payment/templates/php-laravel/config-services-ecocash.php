<?php

// Add this entry to the array returned by config/services.php.

return [
    'ecocash' => [
        'base_url'            => env('EIP_BASE_URL', 'https://developers.ecocash.co.zw/sandbox/payment/v1'),
        'username'            => env('EIP_USERNAME'),
        'password'            => env('EIP_PASSWORD'),
        'merchant_code'       => env('EIP_MERCHANT_CODE'),
        'merchant_pin'        => env('EIP_MERCHANT_PIN'),
        'merchant_number'     => env('EIP_MERCHANT_NUMBER'),
        'terminal_id'         => env('EIP_TERMINAL_ID'),
        'merchant_name'       => env('EIP_MERCHANT_NAME'),
        'super_merchant_name' => env('EIP_SUPER_MERCHANT_NAME'),
        'channel'             => env('EIP_CHANNEL', 'WEB'),
        'location'            => env('EIP_LOCATION', 'Harare'),
        'refund_tran_type'    => env('EIP_REFUND_TRAN_TYPE', 'REF'),
    ],
];
