<?php

namespace App;

use Illuminate\Database\Eloquent\Model;

class GroupAssignment extends Model
{
    //
    protected $dates = [ 
        'valid_from',
        'valid_to',
        'changed_at',
    ];
}
