<?php
use App\User;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

/**
 * Register any application authentication / authorization services.
 *
 * @return void
 */
public function boot()
{
    $this->registerPolicies();

    Auth::viaRequest('simple-token', function ($request) {
        print($request);
        return User::where('api_token', $request->token)->first();
    });
}

?>
