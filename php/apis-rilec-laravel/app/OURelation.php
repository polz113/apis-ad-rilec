<?php

namespace App;

use Illuminate\Database\Eloquent\Model;

class OURelation extends Model
{
    //
    protected $dates = [ 
        'valid_from',
        'valid_to',
        'changed_at',
        'generated_at',
    ];
}
